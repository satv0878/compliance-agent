FROM golang:1.21-alpine AS builder

WORKDIR /app

COPY go.mod ./
RUN go mod download
COPY main.go ./
RUN go get github.com/aws/aws-sdk-go/aws
RUN go get github.com/aws/aws-sdk-go/aws/credentials  
RUN go get github.com/aws/aws-sdk-go/aws/session
RUN go get github.com/aws/aws-sdk-go/service/s3
RUN go get github.com/elastic/go-elasticsearch/v7
RUN go get github.com/gin-gonic/gin
RUN go build -o hashwriter main.go

FROM alpine:latest

RUN apk --no-cache add ca-certificates

WORKDIR /root/

COPY --from=builder /app/hashwriter .

EXPOSE 8003

CMD ["./hashwriter"]