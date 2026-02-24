#!/bin/sh
# Generate Hugo blog posts from all git commits in a repo
# Usage: ./scripts/commits-to-posts.sh <repo-dir> [blog-dir]
#
# Creates one post per commit in content/posts/commits/

set -e

REPO_DIR="${1:-.}"
BLOG_DIR="${2:-/opt/bojemoi/blog-repo}"
POSTS_DIR="$BLOG_DIR/content/posts/commits"

# Derive repo name from git remote or directory name
REPO_NAME=$(cd "$REPO_DIR" && git remote get-url origin 2>/dev/null | sed 's|.*/||; s|\.git$||' || basename "$REPO_DIR")

mkdir -p "$POSTS_DIR"

cd "$REPO_DIR"

echo "=== $REPO_NAME ($REPO_DIR) ==="

# Iterate commits oldest-first
git log --format="%H" --reverse | while read -r HASH; do
    SHORT=$(echo "$HASH" | cut -c1-7)
    AUTHOR=$(git log -1 --format="%an" "$HASH")
    DATE=$(git log -1 --format="%aI" "$HASH")
    DATE_SHORT=$(echo "$DATE" | cut -c1-10)
    SUBJECT=$(git log -1 --format="%s" "$HASH")
    BODY=$(git log -1 --format="%b" "$HASH")

    FILENAME="$DATE_SHORT-$REPO_NAME-$SHORT.md"
    FILEPATH="$POSTS_DIR/$FILENAME"

    # Skip if post already exists
    if [ -f "$FILEPATH" ]; then
        echo "SKIP $SHORT - $SUBJECT"
        continue
    fi

    # Get diff stats
    SHORTSTAT=$(git diff-tree --shortstat --no-commit-id "$HASH" 2>/dev/null || true)
    FILES_CHANGED=$(git diff-tree --no-commit-id --name-status -r "$HASH" 2>/dev/null || true)

    # Determine tags from commit message
    TAGS="\"commit\", \"$REPO_NAME\""
    case "$SUBJECT" in
        Fix*|fix*) TAGS="$TAGS, \"fix\"" ;;
        Add*|add*) TAGS="$TAGS, \"feature\"" ;;
        *refactor*|*Refactor*) TAGS="$TAGS, \"refactor\"" ;;
        *test*|*Test*) TAGS="$TAGS, \"test\"" ;;
    esac

    # Detect components from changed files
    for component in stack borodino samsonov provisioning volumes; do
        if echo "$FILES_CHANGED" | grep -q "$component"; then
            TAGS="$TAGS, \"$component\""
        fi
    done

    # Count files
    FILE_COUNT=$(echo "$FILES_CHANGED" | grep -c '.' 2>/dev/null || echo "0")

    # Build the post
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
| **Branch** | \`main\` |
| **Auteur** | $AUTHOR |
| **Hash** | \`$HASH\` |
| **Date** | $DATE_SHORT |
FRONTMATTER

    # Add body if present
    if [ -n "$BODY" ]; then
        cat >> "$FILEPATH" << EOF

### Description

$BODY
EOF
    fi

    # Add files changed
    if [ -n "$FILES_CHANGED" ]; then
        cat >> "$FILEPATH" << EOF

### Fichiers modifiés

\`\`\`
$FILES_CHANGED
\`\`\`
EOF
    fi

    # Add stats
    if [ -n "$SHORTSTAT" ]; then
        cat >> "$FILEPATH" << EOF

### Statistiques

\`\`\`
$SHORTSTAT
\`\`\`
EOF
    fi

    echo "CREATE $SHORT - $SUBJECT"
done

echo "Done for $REPO_NAME."
