#!/usr/bin/env bash

set -o errtrace -o nounset -o pipefail -o errexit

# Goto directory of this script
cd "$(dirname "${BASH_SOURCE[0]}")"

linting () {
  echo "############################################"
  echo "#                                          #"
  echo "#        Linting                           #"
  echo "#                                          #"
  echo "############################################"
  docker run --rm -i hadolint/hadolint < Dockerfile
}

integration_tests () {
  echo "############################################"
  echo "#                                          #"
  echo "#        Integration testing               #"
  echo "#                                          #"
  echo "############################################"
  FILE=canon_eos_70d_02
  (mkdir raw && cd raw && wget "https://img.photographyblog.com/reviews/canon_eos_70d/photos/${FILE}.cr2")
  docker run --rm -v "${PWD}":/tmp -it "$(docker build -q .)"
  if [ ! -f "./jpg/${FILE}.jpg" ]; then
    echo "$FILE was not created"
    exit 1
  fi
}

check_for_clean_worktree() {
  echo "############################################"
  echo "#                                          #"
  echo "#        Check for clean worktree          #"
  echo "#                                          #"
  echo "############################################"
  # To be executed after all other steps, to ensures that there is no
  # uncommitted code and there are no untracked files, which means .gitignore is
  # complete and all code is part of a reviewable commit.
  GIT_STATUS="$(git status --porcelain)"
  if [[ $GIT_STATUS ]]; then
    echo "Your worktree is not clean, there is either uncommitted code or there are untracked files:"
    echo "${GIT_STATUS}"
    exit 1
  fi
}

linting
integration_tests
check_for_clean_worktree
