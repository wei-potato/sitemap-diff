module.exports = {
  apps: [{
    name: 'samwise-daily-job',
    script: 'python -m jobs.main',  // 你的脚本路径
    cron: '0 8 * * *',
    autorestart: false,
    watch: false,
    instances: 1
  }]
}