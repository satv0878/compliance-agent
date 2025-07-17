package main

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"os"
	"sync"
	"time"

	"github.com/aws/aws-sdk-go/aws"
	"github.com/aws/aws-sdk-go/aws/credentials"
	"github.com/aws/aws-sdk-go/aws/session"
	"github.com/aws/aws-sdk-go/service/s3"
	"github.com/elastic/go-elasticsearch/v7"
	"github.com/gin-gonic/gin"
)

type HashRequest struct {
	MessageID         string                 `json:"message_id"`
	ChannelID         string                 `json:"channel_id"`
	MessageType       string                 `json:"message_type"`
	Timestamp         time.Time              `json:"timestamp"`
	ValidationResults []ValidationResult     `json:"validation_results"`
	OverallStatus     string                 `json:"overall_status"`
	ParsedData        map[string]interface{} `json:"parsed_data"`
}

type ValidationResult struct {
	RuleID   string `json:"rule_id"`
	Passed   bool   `json:"passed"`
	Severity string `json:"severity"`
	Message  string `json:"message"`
}

type HashEntry struct {
	Timestamp      time.Time              `json:"ts"`
	MessageID      string                 `json:"message_id"`
	MessageType    string                 `json:"msgType"`
	SHA256Payload  string                 `json:"sha256_payload"`
	PrevHash       string                 `json:"prevHash"`
	ChainHash      string                 `json:"chainHash"`
	ChannelID      string                 `json:"channel_id"`
	ValidationData map[string]interface{} `json:"validation_data"`
	Severity       string                 `json:"severity"`
}

type HashWriter struct {
	esClient    *elasticsearch.Client
	s3Client    *s3.S3
	bucketName  string
	indexPrefix string
	prevHash    string
	mutex       sync.Mutex
}

func NewHashWriter() (*HashWriter, error) {
	// Elasticsearch configuration
	cfg := elasticsearch.Config{
		Addresses: []string{
			fmt.Sprintf("http://%s:%s", 
				getEnv("ES_HOST", "localhost"),
				getEnv("ES_PORT", "9200")),
		},
		Username: getEnv("ES_USERNAME", "elastic"),
		Password: getEnv("ES_PASSWORD", "changeme"),
	}
	
	esClient, err := elasticsearch.NewClient(cfg)
	if err != nil {
		return nil, fmt.Errorf("error creating Elasticsearch client: %s", err)
	}

	// S3 configuration
	sess, err := session.NewSession(&aws.Config{
		Endpoint:         aws.String(getEnv("S3_ENDPOINT", "http://localhost:9000")),
		Region:           aws.String(getEnv("S3_REGION", "us-east-1")),
		Credentials:      credentials.NewStaticCredentials(
			getEnv("S3_ACCESS_KEY", "minioadmin"),
			getEnv("S3_SECRET_KEY", "minioadmin"),
			""),
		S3ForcePathStyle: aws.Bool(true),
	})
	if err != nil {
		return nil, fmt.Errorf("error creating S3 session: %s", err)
	}

	return &HashWriter{
		esClient:    esClient,
		s3Client:    s3.New(sess),
		bucketName:  getEnv("S3_BUCKET", "compliance-audit"),
		indexPrefix: getEnv("ES_INDEX_PREFIX", "audit"),
		prevHash:    "0000000000000000000000000000000000000000000000000000000000000000",
	}, nil
}

func (hw *HashWriter) generateHash(data []byte) string {
	hash := sha256.Sum256(data)
	return hex.EncodeToString(hash[:])
}

func (hw *HashWriter) processHash(c *gin.Context) {
	var req HashRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	// Lock for chain consistency
	hw.mutex.Lock()
	defer hw.mutex.Unlock()

	// Create payload hash
	payloadData, _ := json.Marshal(req.ParsedData)
	payloadHash := hw.generateHash(payloadData)

	// Create chain hash
	chainData := fmt.Sprintf("%s|%s|%s|%s", 
		req.Timestamp.Format(time.RFC3339),
		req.MessageID,
		payloadHash,
		hw.prevHash)
	chainHash := hw.generateHash([]byte(chainData))

	// Create hash entry
	entry := HashEntry{
		Timestamp:      req.Timestamp,
		MessageID:      req.MessageID,
		MessageType:    req.MessageType,
		SHA256Payload:  payloadHash,
		PrevHash:       hw.prevHash,
		ChainHash:      chainHash,
		ChannelID:      req.ChannelID,
		ValidationData: map[string]interface{}{
			"results": req.ValidationResults,
			"status":  req.OverallStatus,
		},
		Severity: req.OverallStatus,
	}

	// Store in Elasticsearch
	indexName := fmt.Sprintf("%s-%s", hw.indexPrefix, req.Timestamp.Format("2006.01.02"))
	entryJSON, _ := json.Marshal(entry)
	
	res, err := hw.esClient.Index(
		indexName,
		bytes.NewReader(entryJSON),
		hw.esClient.Index.WithDocumentID(req.MessageID),
		hw.esClient.Index.WithRefresh("true"),
	)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": fmt.Sprintf("Error indexing document: %s", err)})
		return
	}
	defer res.Body.Close()

	// Store in S3 with object lock
	objectKey := fmt.Sprintf("%s/%s/%s.json",
		req.Timestamp.Format("2006/01/02"),
		req.ChannelID,
		req.MessageID)
	
	_, err = hw.s3Client.PutObject(&s3.PutObjectInput{
		Bucket:               aws.String(hw.bucketName),
		Key:                  aws.String(objectKey),
		Body:                 bytes.NewReader(entryJSON),
		ContentType:          aws.String("application/json"),
		ServerSideEncryption: aws.String("AES256"),
		ObjectLockMode:       aws.String("COMPLIANCE"),
		ObjectLockRetainUntilDate: aws.Time(time.Now().AddDate(10, 0, 0)), // 10 years
	})
	if err != nil {
		log.Printf("Warning: Failed to store in S3: %v", err)
	}

	// Update previous hash for next entry
	hw.prevHash = chainHash

	c.JSON(http.StatusOK, gin.H{
		"chain_hash":    chainHash,
		"payload_hash":  payloadHash,
		"prev_hash":     entry.PrevHash,
		"es_index":      indexName,
		"s3_key":        objectKey,
	})
}

func (hw *HashWriter) getChainStatus(c *gin.Context) {
	c.JSON(http.StatusOK, gin.H{
		"current_hash": hw.prevHash,
		"timestamp":    time.Now(),
		"status":       "active",
	})
}

func getEnv(key, defaultValue string) string {
	if value := os.Getenv(key); value != "" {
		return value
	}
	return defaultValue
}

func main() {
	gin.SetMode(gin.ReleaseMode)
	
	hw, err := NewHashWriter()
	if err != nil {
		log.Fatalf("Failed to initialize hash writer: %v", err)
	}

	router := gin.Default()
	
	router.POST("/hash", hw.processHash)
	router.GET("/status", hw.getChainStatus)
	router.GET("/health", func(c *gin.Context) {
		c.JSON(http.StatusOK, gin.H{
			"status":    "healthy",
			"timestamp": time.Now(),
		})
	})

	port := getEnv("PORT", "8003")
	log.Printf("Hash Writer Service starting on port %s", port)
	if err := router.Run(":" + port); err != nil {
		log.Fatalf("Failed to start server: %v", err)
	}
}