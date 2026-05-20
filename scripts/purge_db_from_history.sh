#!/bin/bash
# scripts/purge_db_from_history.sh
# Guided script to remove accidental database commits from history.

set -e

DB_FILE="agent_memory.db"

echo "⚠️  CRITICAL: This script will scrub $DB_FILE from your ENTIRE git history."
echo "Ensure you have a backup of the database file itself if you need the data."
read -p "Are you sure you want to proceed? (y/N): " confirm

if [[ $confirm != [yY] ]]; then
    echo "Aborting."
    exit 1
fi

# Step 1: Remove from current index
echo "Step 1: Removing $DB_FILE from current index..."
git rm --cached $DB_FILE || echo "$DB_FILE not in index, skipping."

# Step 2: Commit the removal
echo "Step 2: Committing the removal..."
git commit -m "Cleanup: Untrack $DB_FILE" || echo "Nothing to commit."

# Step 3: Scrub history (requires git-filter-repo)
if command -v git-filter-repo &> /dev/null; then
    echo "Step 3: Scrubbing history using git-filter-repo..."
    git filter-repo --path $DB_FILE --invert-paths --force
else
    echo "❌ ERROR: git-filter-repo not found."
    echo "Install it via: pip install git-filter-repo"
    echo "Then re-run this script."
    exit 1
fi

echo "✅ SUCCESS: $DB_FILE has been purged from history."
echo "⚠️  MANDATORY NEXT STEPS:"
echo "1. Coordinate with your team: everyone must delete their local clone and re-clone."
echo "2. Force-push to the remote: git push origin master --force"
