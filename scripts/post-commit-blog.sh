#!/bin/sh
# Post-commit hook: generate a Hugo blog post from the latest commit
# and push it to the blog repo.
#
# Installed as .git/hooks/post-commit (symlink) in each repo.

BLOG_DIR="/opt/bojemoi/blog-repo"
POSTS_DIR="$BLOG_DIR/content/posts/commits"

# Capture source repo context BEFORE any cd
SOURCE_DIR="$(git rev-parse --show-toplevel)"
REPO_NAME=$(git -C "$SOURCE_DIR" remote get-url origin 2>/dev/null | sed 's|.*/||; s|\.git$||')
[ -z "$REPO_NAME" ] && REPO_NAME=$(basename "$SOURCE_DIR")
BRANCH=$(git -C "$SOURCE_DIR" rev-parse --abbrev-ref HEAD)

HASH=$(git -C "$SOURCE_DIR" rev-parse HEAD)
SHORT=$(echo "$HASH" | cut -c1-7)
AUTHOR=$(git -C "$SOURCE_DIR" log -1 --format="%an" "$HASH")
DATE=$(git -C "$SOURCE_DIR" log -1 --format="%aI" "$HASH")
DATE_SHORT=$(echo "$DATE" | cut -c1-10)
SUBJECT=$(git -C "$SOURCE_DIR" log -1 --format="%s" "$HASH")
BODY=$(git -C "$SOURCE_DIR" log -1 --format="%b" "$HASH")

FILENAME="$DATE_SHORT-$REPO_NAME-$SHORT.md"
FILEPATH="$POSTS_DIR/$FILENAME"

mkdir -p "$POSTS_DIR"

# Skip if already exists
[ -f "$FILEPATH" ] && exit 0

# Diff stats
SHORTSTAT=$(git -C "$SOURCE_DIR" diff-tree --shortstat --no-commit-id "$HASH" 2>/dev/null || true)
FILES_CHANGED=$(git -C "$SOURCE_DIR" diff-tree --no-commit-id --name-status -r "$HASH" 2>/dev/null || true)

# Auto-tags
TAGS="\"commit\", \"$REPO_NAME\""
case "$SUBJECT" in
    Fix*|fix*) TAGS="$TAGS, \"fix\"" ;;
    Add*|add*) TAGS="$TAGS, \"feature\"" ;;
    *refactor*|*Refactor*) TAGS="$TAGS, \"refactor\"" ;;
    *test*|*Test*) TAGS="$TAGS, \"test\"" ;;
esac
for component in stack borodino samsonov provisioning volumes; do
    echo "$FILES_CHANGED" | grep -q "$component" && TAGS="$TAGS, \"$component\""
done

FILE_COUNT=$(echo "$FILES_CHANGED" | grep -c '.' 2>/dev/null || echo "0")

# Write the post
cat > "$FILEPATH" << FRONTMATTER
---
title: "[$REPO_NAME] $SUBJECT"
date: $DATE
draft: false
tags: [$TAGS]
categories: ["Git Activity"]
summary: "Commit $SHORT par $AUTHOR — $FILE_COUNT fichier(s) modifié(s)"
author: "$AUTHOR"
---

## Commit \`$SHORT\`

| | |
|---|---|
| **Repository** | $REPO_NAME |
| **Branch** | \`$BRANCH\` |
| **Auteur** | $AUTHOR |
| **Hash** | \`$HASH\` |
| **Date** | $DATE_SHORT |
FRONTMATTER

if [ -n "$BODY" ]; then
    cat >> "$FILEPATH" << EOF

### Description

$BODY
EOF
fi

if [ -n "$FILES_CHANGED" ]; then
    cat >> "$FILEPATH" << EOF

### Fichiers modifiés

\`\`\`
$FILES_CHANGED
\`\`\`
EOF
fi

if [ -n "$SHORTSTAT" ]; then
    cat >> "$FILEPATH" << EOF

### Statistiques

\`\`\`
$SHORTSTAT
\`\`\`
EOF
fi

# Commit and push to blog repo (no-verify to avoid recursive hooks)
cd "$BLOG_DIR"
git add "$FILEPATH"
git commit -m "Auto-post: [$REPO_NAME] $SHORT - $SUBJECT" --no-verify 2>/dev/null || true
git push origin main 2>/dev/null &

echo "[blog] Post created: $FILENAME"
