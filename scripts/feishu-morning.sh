#!/bin/bash
# 飞书早安消息推送

curl -s -X POST "https://open.feishu.cn/open-apis/bot/v2/hook/c4dea7a3-ccdc-4357-830d-8cebc95b55b9" \
  -H "Content-Type: application/json" \
  -d '{"msg_type":"text","content":{"text":"早上好！新的一天开始了 ☀️"}}'
