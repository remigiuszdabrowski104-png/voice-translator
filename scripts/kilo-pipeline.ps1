# kilo-pipeline.ps1
# Kilo multi-agent pipeline - respects per-mode model and permissions
# Flow: Code -> Review#1 -> Debug(if needed) -> Tester -> [Review -> Debug] loop (max 2 fix rounds)

[CmdletBinding()]
param(
    [Parameter(ValueFromRemainingArguments=$true)]
    [string[]]$ImplementArgs
)

$ErrorActionPreference = "Continue"
$pipelineDir = ".kilo\pipeline"
New-Item -ItemType Directory -Force -Path $pipelineDir | Out-Null

# Hard limit on fix rounds (cost safety). Each round = 1 review + 1 debug.
$MaxFixRounds = 2

function Write-Phase {
    param($Name)
    Write-Host ""
    Write-Host "===========================================" -ForegroundColor Cyan
    Write-Host "  $Name" -ForegroundColor Cyan
    Write-Host "===========================================" -ForegroundColor Cyan
}

# ---------------------------------------------------------------------------
# PHASE 1: Implementation (code agent -> DeepSeek V4 Pro)
# ---------------------------------------------------------------------------
Write-Phase "PHASE: Implementation (code agent / DeepSeek V4 Pro)"
$implementMsg = "/speckit.implement " + ($ImplementArgs -join " ")
kilo run --agent code $implementMsg

# ---------------------------------------------------------------------------
# PHASE 2: First Review (reviewer agent -> Sonnet)
# ---------------------------------------------------------------------------
Write-Phase "PHASE: First Review (reviewer agent / Sonnet)"
$reviewPrompt = @'
Review the implementation just completed.

Process:
1. Read all changed files in src/ and tests/ (use git diff HEAD to identify)
2. Read the spec and contracts in specs/ if present
3. Apply the code-review-and-quality skill from .claude/skills/code-review-and-quality/SKILL.md

Output format (REQUIRED):
CODE REVIEW REPORT
==================
Files reviewed: [list]

BLOCKER (count): [findings]
MAJOR (count): [findings]
MINOR (count): [findings]
SUGGESTIONS (count): [findings]

VERDICT: APPROVE | REQUEST_CHANGES

Final line MUST be exactly "VERDICT: APPROVE" or "VERDICT: REQUEST_CHANGES".
'@

$review1Output = kilo run --agent reviewer $reviewPrompt 2>&1 | Out-String
$review1Output | Out-File -FilePath "$pipelineDir\review-1.md" -Encoding UTF8
Write-Host $review1Output

if ($review1Output -match "VERDICT:\s*REQUEST_CHANGES") {
    $review1Verdict = "REQUEST_CHANGES"
    Write-Host ""
    Write-Host "Review #1 verdict: REQUEST_CHANGES" -ForegroundColor Yellow
} else {
    $review1Verdict = "APPROVE"
    Write-Host ""
    Write-Host "Review #1 verdict: APPROVE" -ForegroundColor Green
}

# ---------------------------------------------------------------------------
# PHASE 3: Debug (conditional, debug agent -> Sonnet)
# Runs only if the first review requested changes.
# ---------------------------------------------------------------------------
if ($review1Verdict -eq "REQUEST_CHANGES") {
    Write-Phase "PHASE: Debug (debug agent / Sonnet)"
    $debugPrompt = @"
The reviewer found issues. Read the report at $pipelineDir\review-1.md and fix them.

Process:
1. Read $pipelineDir\review-1.md for findings
2. Fix all BLOCKER and MAJOR issues
3. Fix MINOR issues if straightforward
4. Run pytest after each fix to verify no regression
5. Apply debugging-and-error-recovery skill from .claude/skills/

Report at the end:
- Total fixes applied
- Bonus issues found and fixed
- Final pytest result (X/Y passed)
"@
    kilo run --agent debug $debugPrompt
} else {
    Write-Host "Debug skipped - approved on first review" -ForegroundColor Green
}

# ---------------------------------------------------------------------------
# PHASE 4: Tester (tester agent -> DeepSeek V4 Flash)
# ---------------------------------------------------------------------------
Write-Phase "PHASE: Tester (tester agent / DeepSeek V4 Flash)"
$testerPrompt = @'
Verify and extend test coverage.

Process:
1. Run pytest - confirm pass rate
2. Identify missing critical edge cases (boundaries, special floats, errors)
3. Add MAXIMUM 3 most critical missing edge case tests
4. Run pytest again - all must pass
5. Apply test-driven-development skill from .claude/skills/

IMPORTANT when comparing floating-point results: always use pytest.approx
(or math.isclose). Never assert exact equality on float arithmetic results.

Report at the end:
- Initial test count
- Edge cases added (max 3)
- Final test count and pytest result
'@
kilo run --agent tester $testerPrompt

# ---------------------------------------------------------------------------
# FIX LOOP: Review (code + tests together) -> Debug, up to $MaxFixRounds rounds.
# Runs ALWAYS, so a buggy test added by the Tester is caught and fixed.
# ---------------------------------------------------------------------------
$finalVerdict = "NEEDS_ATTENTION"
$round = 0

while ($round -lt $MaxFixRounds) {
    $round++

    Write-Phase "PHASE: Review round $round/$MaxFixRounds (reviewer agent / Sonnet)"
    $loopReviewPrompt = @"
Holistic review of the CURRENT state of the project (production code AND tests together).

Process:
1. Use git diff HEAD to see all changes; read every changed file in src/ and tests/
2. Run pytest yourself is NOT your job - but reason about whether the tests are correct
   (e.g. floating-point asserts must use pytest.approx, not exact ==)
3. Check production code for BLOCKER/MAJOR issues
4. Check the TESTS themselves for bugs (wrong expected values, exact float compares,
   tests that would not actually run, disabled/skipped tests)
5. Apply the code-review-and-quality skill from .claude/skills/code-review-and-quality/SKILL.md

Output format (REQUIRED):
REVIEW REPORT (round $round)
============================
Files reviewed: [list]

BLOCKER (count): [findings - include file:line and whether it is in production code or a test]
MAJOR (count): [findings]
MINOR (count): [findings]
SUGGESTIONS (count): [findings]

VERDICT: APPROVE | REQUEST_CHANGES

Final line MUST be exactly "VERDICT: APPROVE" or "VERDICT: REQUEST_CHANGES".
"@
    $loopReviewOutput = kilo run --agent reviewer $loopReviewPrompt 2>&1 | Out-String
    $loopReviewOutput | Out-File -FilePath "$pipelineDir\review-loop-$round.md" -Encoding UTF8
    Write-Host $loopReviewOutput

    if ($loopReviewOutput -match "VERDICT:\s*APPROVE") {
        $finalVerdict = "READY_TO_MERGE"
        Write-Host ""
        Write-Host "Review round ${round}: APPROVE" -ForegroundColor Green
        break
    }

    Write-Host ""
    Write-Host "Review round ${round}: REQUEST_CHANGES" -ForegroundColor Yellow

    # If this was the last allowed round, stop here without another debug pass.
    if ($round -ge $MaxFixRounds) {
        Write-Host "Reached max fix rounds ($MaxFixRounds) - stopping." -ForegroundColor Red
        break
    }

    Write-Phase "PHASE: Fix round $round/$MaxFixRounds (debug agent / Sonnet)"
    $loopDebugPrompt = @"
The reviewer requested changes. Read $pipelineDir\review-loop-$round.md and fix EVERYTHING it lists.

Process:
1. Read $pipelineDir\review-loop-$round.md for findings
2. Fix all BLOCKER and MAJOR issues - these may be in production code (src/) OR in tests (tests/)
3. If a TEST is wrong (e.g. exact float compare like 'assert x == 4.3'), fix the test to use
   pytest.approx. Do NOT delete or disable tests to make them pass.
4. Run pytest after fixing to confirm all tests pass
5. Apply debugging-and-error-recovery skill from .claude/skills/

Report at the end:
- Findings addressed (BLOCKER/MAJOR)
- Files changed (src/ vs tests/)
- Final pytest result (X/Y passed)
"@
    kilo run --agent debug $loopDebugPrompt
}

# ---------------------------------------------------------------------------
# FINAL REPORT
# ---------------------------------------------------------------------------
Write-Host ""
Write-Host "===========================================" -ForegroundColor Magenta
Write-Host "  PIPELINE COMPLETE" -ForegroundColor Magenta
Write-Host "===========================================" -ForegroundColor Magenta

Write-Host "Final status: " -NoNewline
if ($finalVerdict -eq "READY_TO_MERGE") {
    Write-Host $finalVerdict -ForegroundColor Green
} else {
    Write-Host $finalVerdict -ForegroundColor Red
    Write-Host "  (review still requested changes after $MaxFixRounds fix round(s) - see reports)" -ForegroundColor Red
}

Write-Host ""
Write-Host "Reports in: $pipelineDir\"
Write-Host "  - review-1.md            (first review)"
for ($i = 1; $i -le $round; $i++) {
    Write-Host "  - review-loop-$i.md       (fix-loop review round $i)"
}

Write-Host ""
Write-Host "Token usage and cost:" -ForegroundColor Yellow
kilo stats
