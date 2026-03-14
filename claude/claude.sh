#docker build -t claude-code .
docker run -it  --name claude \
  -e ANTHROPIC_API_KEY="gBupVVLYe95nNaA4paX9HT45H90KZni3TujGnqtzGe6Xj7O0#2wsw_nane2auIKie8zUxnBO-8RTdTvE8zrw22D2ILr4" \
  -v /opt/bojemoi:/workspace \
  -v ~/.claude:/root/.claude \
  -v ~/.gitconfig:/root/.gitconfig:ro \
  -v ~/.ssh:/root/.ssh:ro
  -w /workspace \
  claude-code
