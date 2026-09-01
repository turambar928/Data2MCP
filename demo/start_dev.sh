#!/bin/bash

# 启动前端开发服务器（使用正确的 Node.js 版本）

# 加载 nvm
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"

# 切换到项目目录
cd "$(dirname "$0")"

# 使用 Node 25
nvm use 25 2>/dev/null || nvm use system

# 启动 Vite
npm run dev
