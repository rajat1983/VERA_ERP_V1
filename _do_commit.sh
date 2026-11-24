#!/usr/bin/env bash

set -euo pipefail

cd /home/rajat/vera-erp

git add -A

git reset -- static/uploads/users/user_1_1787468980.jpeg

git status --short

git commit -m "Add tenant isolation, billing, entitlements, extra seats, and Super Admin plan UI."

git status

rm -f /home/rajat/vera-erp/_do_commit.sh
