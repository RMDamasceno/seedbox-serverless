resource "aws_security_group" "worker" {
  name        = "${var.project_name}-worker-sg"
  description = "Worker EC2 Security Group - no inbound, restricted outbound"
  vpc_id      = var.vpc_id

  # Outbound: HTTPS (S3, AWS APIs)
  egress {
    description = "HTTPS for S3 and AWS APIs"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # Outbound: BitTorrent TCP
  egress {
    description = "BitTorrent TCP"
    from_port   = 6881
    to_port     = 6889
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # Outbound: BitTorrent UDP
  egress {
    description = "BitTorrent UDP"
    from_port   = 6881
    to_port     = 6889
    protocol    = "udp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # Outbound: DNS
  egress {
    description = "DNS"
    from_port   = 53
    to_port     = 53
    protocol    = "udp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # Outbound: HTTP (para downloads de pacotes na instalação)
  egress {
    description = "HTTP for package installation"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.project_name}-worker-sg"
  }
}
