#!/bin/bash
# Smart Git Workflow Automation
# Intelligent commit, branch management, and collaboration

set -e

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}🚀 Smart Git Workflow Automation${NC}"
echo "==============================="

# Create git hooks directory
mkdir -p .git/hooks

# Function to setup git hooks
setup_git_hooks() {
    echo -e "${BLUE}Setting up Git hooks...${NC}"

    # Pre-commit hook
    cat > .git/hooks/pre-commit << 'EOF'
#!/bin/bash
echo "🔍 Running pre-commit checks..."

# Run quality checks
if [ -f "automate.sh" ]; then
    ./automate.sh quality
    if [ $? -ne 0 ]; then
        echo "❌ Quality checks failed. Fix issues before committing."
        exit 1
    fi
fi

# Run tests
if [ -f "automate.sh" ]; then
    ./automate.sh test
    if [ $? -ne 0 ]; then
        echo "❌ Tests failed. Fix issues before committing."
        exit 1
    fi
fi

echo "✅ Pre-commit checks passed!"
EOF

    # Pre-push hook
    cat > .git/hooks/pre-push << 'EOF'
#!/bin/bash
echo "🚀 Running pre-push checks..."

# Run security checks
if [ -f "manage-dependencies.sh" ]; then
    ./manage-dependencies.sh check
    if [ $? -ne 0 ]; then
        echo "⚠️  Security issues found. Consider fixing before pushing."
        # Don't block push for security issues, just warn
    fi
fi

# Check for large files
LARGE_FILES=$(find . -type f -size +50M | grep -v .git | wc -l)
if [ "$LARGE_FILES" -gt 0 ]; then
    echo "⚠️  Large files detected. Consider using Git LFS."
fi

echo "✅ Pre-push checks completed!"
EOF

    # Make hooks executable
    chmod +x .git/hooks/pre-commit
    chmod +x .git/hooks/pre-push

    echo -e "${GREEN}✓ Git hooks installed${NC}"
}

# Function to create smart commit
smart_commit() {
    echo -e "${BLUE}Creating smart commit...${NC}"

    # Check git status
    if [ -z "$(git status --porcelain)" ]; then
        echo "No changes to commit"
        return 0
    fi

    # Analyze changes
    CHANGED_FILES=$(git diff --cached --name-only | wc -l)
    NEW_FILES=$(git diff --cached --name-only --diff-filter=A | wc -l)
    MODIFIED_FILES=$(git diff --cached --name-only --diff-filter=M | wc -l)
    DELETED_FILES=$(git diff --cached --name-only --diff-filter=D | wc -l)

    # Generate commit message based on changes
    if [ "$NEW_FILES" -gt 0 ] && [ "$MODIFIED_FILES" -eq 0 ]; then
        TYPE="feat"
        SCOPE="add"
    elif [ "$MODIFIED_FILES" -gt 0 ] && [ "$NEW_FILES" -eq 0 ]; then
        TYPE="fix"
        SCOPE="update"
    elif [ "$DELETED_FILES" -gt 0 ]; then
        TYPE="chore"
        SCOPE="remove"
    else
        TYPE="refactor"
        SCOPE="improve"
    fi

    # Get main changed file types
    MAIN_TYPES=$(git diff --cached --name-only | sed 's/.*\.//' | sort | uniq -c | sort -nr | head -3 | awk '{print $2}' | tr '\n' ' ' | sed 's/ $//')

    # Generate commit message
    COMMIT_MSG="$TYPE: $SCOPE $MAIN_TYPES files"

    # Add more context
    if [ "$CHANGED_FILES" -gt 10 ]; then
        COMMIT_MSG="$COMMIT_MSG (bulk update)"
    fi

    echo "Suggested commit message: $COMMIT_MSG"
    read -p "Use this message? (Y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Nn]$ ]]; then
        git commit -m "$COMMIT_MSG"
        echo -e "${GREEN}✓ Smart commit created${NC}"
    else
        echo "Please enter your commit message:"
        read -r CUSTOM_MSG
        git commit -m "$CUSTOM_MSG"
        echo -e "${GREEN}✓ Custom commit created${NC}"
    fi
}

# Function to create feature branch
create_feature_branch() {
    echo -e "${BLUE}Creating feature branch...${NC}"

    read -p "Feature name: " FEATURE_NAME
    BRANCH_NAME="feature/$(echo "$FEATURE_NAME" | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9]/-/g')"

    git checkout -b "$BRANCH_NAME"
    echo -e "${GREEN}✓ Created and switched to branch: $BRANCH_NAME${NC}"
}

# Function to smart merge
smart_merge() {
    echo -e "${BLUE}Smart merge operation...${NC}"

    CURRENT_BRANCH=$(git branch --show-current)

    if [[ $CURRENT_BRANCH == feature/* ]]; then
        BASE_BRANCH="develop"
        if ! git show-ref --verify --quiet refs/heads/develop; then
            BASE_BRANCH="main"
        fi

        echo "Merging $CURRENT_BRANCH into $BASE_BRANCH"

        # Update base branch
        git checkout "$BASE_BRANCH"
        git pull origin "$BASE_BRANCH"

        # Merge feature branch
        git checkout "$CURRENT_BRANCH"
        git rebase "$BASE_BRANCH"

        # Merge back
        git checkout "$BASE_BRANCH"
        git merge "$CURRENT_BRANCH"

        echo -e "${GREEN}✓ Smart merge completed${NC}"
    else
        echo "Not on a feature branch. Use regular git merge."
    fi
}

# Function to cleanup branches
cleanup_branches() {
    echo -e "${BLUE}Cleaning up branches...${NC}"

    # Delete merged branches
    git branch --merged | grep -v "\*" | grep -v "main\|master\|develop" | xargs -n 1 git branch -d 2>/dev/null || true

    # Delete remote branches that no longer exist
    git remote prune origin 2>/dev/null || true

    echo -e "${GREEN}✓ Branches cleaned up${NC}"
}

# Function to generate changelog
generate_changelog() {
    echo -e "${BLUE}Generating changelog...${NC}"

    LAST_TAG=$(git describe --tags --abbrev=0 2>/dev/null || echo "")

    if [ -z "$LAST_TAG" ]; then
        # First release
        git log --pretty=format:"* %s" > CHANGELOG.md
    else
        # Incremental changelog
        git log "$LAST_TAG"..HEAD --pretty=format:"* %s" > CHANGELOG.tmp

        if [ -f "CHANGELOG.md" ]; then
            mv CHANGELOG.md CHANGELOG.old
            cat CHANGELOG.tmp > CHANGELOG.md
            echo "" >> CHANGELOG.md
            cat CHANGELOG.old >> CHANGELOG.md
            rm CHANGELOG.old
        else
            cat CHANGELOG.tmp > CHANGELOG.md
        fi

        rm CHANGELOG.tmp
    fi

    echo -e "${GREEN}✓ Changelog updated${NC}"
}

# Function to create release
create_release() {
    echo -e "${BLUE}Creating release...${NC}"

    read -p "Release version (e.g., v1.0.0): " VERSION

    # Update version in relevant files
    if [ -f "pyproject.toml" ]; then
        sed -i "s/version = \".*\"/version = \"${VERSION#v}\"/" pyproject.toml
    fi

    if [ -f "package.json" ]; then
        sed -i "s/\"version\": \".*\"/\"version\": \"${VERSION#v}\"/" package.json
    fi

    # Generate changelog
    generate_changelog

    # Commit changes
    git add .
    git commit -m "chore: release $VERSION"

    # Create tag
    git tag "$VERSION"

    echo -e "${GREEN}✓ Release $VERSION created${NC}"
    echo "Push with: git push origin main --tags"
}

# Function to analyze repository health
analyze_repo_health() {
    echo -e "${BLUE}Analyzing repository health...${NC}"

    echo "Repository Statistics:"
    echo "─────────────────────"
    echo "Commits: $(git rev-list --count HEAD)"
    echo "Contributors: $(git shortlog -sn --no-merges | wc -l)"
    echo "Branches: $(git branch -a | wc -l)"
    echo "Tags: $(git tag | wc -l)"

    echo ""
    echo "Code Quality:"
    echo "─────────────"
    echo "Python files: $(find . -name "*.py" -not -path "./.*" | wc -l)"
    echo "Test files: $(find . -name "*test*.py" -o -name "*spec*.py" | wc -l)"
    echo "Documentation: $(find . -name "*.md" -o -name "*.rst" | wc -l)"

    echo ""
    echo "Recent Activity:"
    echo "────────────────"
    git log --oneline -10

    echo -e "${GREEN}✓ Repository analysis completed${NC}"
}

# Function to setup CI/CD
setup_cicd() {
    echo -e "${BLUE}Setting up CI/CD...${NC}"

    mkdir -p .github/workflows

    # Create CI/CD workflow if it doesn't exist
    if [ ! -f ".github/workflows/cicd.yml" ]; then
        cp .github/workflows/cicd.yml .github/workflows/cicd.yml 2>/dev/null || echo "CI/CD template not found"
    fi

    echo -e "${GREEN}✓ CI/CD setup completed${NC}"
}

# Main execution
case "${1:-help}" in
    "setup")
        setup_git_hooks ;;
    "commit")
        smart_commit ;;
    "feature")
        create_feature_branch ;;
    "merge")
        smart_merge ;;
    "cleanup")
        cleanup_branches ;;
    "changelog")
        generate_changelog ;;
    "release")
        create_release ;;
    "health")
        analyze_repo_health ;;
    "cicd")
        setup_cicd ;;
    "all")
        setup_git_hooks
        analyze_repo_health
        setup_cicd ;;
    "help"|"-h"|"--help")
        echo "Smart Git Workflow Automation"
        echo ""
        echo "Usage: $0 [COMMAND]"
        echo ""
        echo "Commands:"
        echo "  setup     - Install git hooks"
        echo "  commit    - Create smart commit"
        echo "  feature   - Create feature branch"
        echo "  merge     - Smart merge feature branch"
        echo "  cleanup   - Clean up merged branches"
        echo "  changelog - Generate changelog"
        echo "  release   - Create new release"
        echo "  health    - Analyze repository health"
        echo "  cicd      - Setup CI/CD pipeline"
        echo "  all       - Setup everything"
        echo "  help      - Show this help"
        echo ""
        echo "Examples:"
        echo "  $0 setup     # Install git hooks"
        echo "  $0 commit    # Smart commit"
        echo "  $0 feature   # Create feature branch"
        ;;
    *)
        echo "Unknown command: $1"
        "$0" help
        exit 1
        ;;
esac

echo -e "${GREEN}Git workflow automation completed!${NC}"