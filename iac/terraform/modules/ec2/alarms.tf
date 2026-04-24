# Alarme: EC2 CPU > 90% por 10 min
resource "aws_cloudwatch_metric_alarm" "worker_cpu" {
  alarm_name          = "${var.project_name}-worker-cpu-high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "CPUUtilization"
  namespace           = "AWS/EC2"
  period              = 300
  statistic           = "Average"
  threshold           = 90
  alarm_description   = "Worker EC2 CPU > 90% for 10 minutes"

  dimensions = {
    AutoScalingGroupName = "${var.project_name}-worker"
  }
}
