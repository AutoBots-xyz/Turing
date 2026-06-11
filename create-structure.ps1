$base = "c:\Users\MAYANK LOT\OneDrive\Documents\python\agri\Turing\nexus"

$files = @(
    ".env.local", ".env.example", ".gitignore", "next.config.mjs", "package.json", "tailwind.config.ts", "tsconfig.json", "README.md",
    "python-engine\main.py", "python-engine\requirements.txt", "python-engine\.env",
    "python-engine\database\database.py", "python-engine\database\models.py", "python-engine\database\crud.py",
    "python-engine\schemas\graph.py", "python-engine\schemas\layer2.py", "python-engine\schemas\layer3.py", "python-engine\schemas\report.py", "python-engine\schemas\run.py",
    "python-engine\services\anthropic_client.py",
    "python-engine\services\layer1\file_detector.py", "python-engine\services\layer1\universal_parser.py", "python-engine\services\layer1\pc_algorithm.py", "python-engine\services\layer1\ontology_builder.py", "python-engine\services\layer1\extractor.py", "python-engine\services\layer1\validator.py", "python-engine\services\layer1\gaussian_process.py", "python-engine\services\layer1\classifier.py",
    "python-engine\services\layer2\bayesian_optimizer.py", "python-engine\services\layer2\agent_explorer.py", "python-engine\services\layer2\agent_exploiter.py", "python-engine\services\layer2\agent_contrarian.py", "python-engine\services\layer2\do_calculus.py", "python-engine\services\layer2\cliff_detector.py", "python-engine\services\layer2\heatmap.py",
    "python-engine\services\layer3\unknown_extractor.py", "python-engine\services\layer3\search_papers.py", "python-engine\services\layer3\search_wikipedia.py", "python-engine\services\layer3\search_web.py", "python-engine\services\layer3\search_patents.py", "python-engine\services\layer3\deduplicator.py", "python-engine\services\layer3\contradiction_detector.py", "python-engine\services\layer3\relation_extractor.py", "python-engine\services\layer3\isomorphism.py", "python-engine\services\layer3\bridge_ranker.py",
    "python-engine\services\layer4\context_packager.py", "python-engine\services\layer4\report_builder.py",
    "python-engine\routers\layer1.py", "python-engine\routers\layer2.py", "python-engine\routers\layer3.py", "python-engine\routers\layer4.py", "python-engine\routers\runs.py",
    "src\app\(dashboard)\dashboard\page.tsx",
    "src\app\(dashboard)\run\[runId]\page.tsx",
    "src\app\(dashboard)\layout.tsx",
    "src\app\layout.tsx", "src\app\page.tsx", "src\app\globals.css",
    "src\components\ui\Button.tsx", "src\components\ui\Input.tsx", "src\components\ui\Card.tsx", "src\components\ui\Modal.tsx", "src\components\ui\Badge.tsx", "src\components\ui\ProgressBar.tsx",
    "src\components\graph\CausalGraph.tsx", "src\components\graph\GraphNode.tsx", "src\components\graph\GraphEdge.tsx", "src\components\graph\BottleneckPulse.tsx", "src\components\graph\CrossDomainBridge.tsx", "src\components\graph\GraphLegend.tsx",
    "src\components\layer1\FileUploader.tsx", "src\components\layer1\ConfidencePanel.tsx",
    "src\components\layer2\AgentStatusPanel.tsx", "src\components\layer2\BestFoundPanel.tsx", "src\components\layer2\Heatmap.tsx", "src\components\layer2\ExperimentHistoryTable.tsx",
    "src\components\layer3\SearchStatusPanel.tsx", "src\components\layer3\BridgeResultsPanel.tsx", "src\components\layer3\MechanismComparison.tsx",
    "src\components\layer4\ReportNav.tsx", "src\components\layer4\ReportSection.tsx", "src\components\layer4\MechanismSection.tsx", "src\components\layer4\ExperimentSection.tsx", "src\components\layer4\BridgesSection.tsx", "src\components\layer4\WarningsSection.tsx", "src\components\layer4\ActionsPanel.tsx", "src\components\layer4\StreamingReport.tsx",
    "src\components\shell\TopNav.tsx", "src\components\shell\LayerProgress.tsx",
    "src\hooks\useRunState.ts", "src\hooks\useGraphAnimation.ts", "src\hooks\useAgentLoop.ts", "src\hooks\useSearchStream.ts", "src\hooks\useReportStream.ts",
    "src\lib\utils.ts",
    "src\types\graph.ts", "src\types\layer2.ts", "src\types\layer3.ts", "src\types\report.ts", "src\types\run.ts"
)

foreach ($f in $files) {
    $path = "$base\$f"
    $dir = Split-Path $path
    if (-not (Test-Path $dir)) {
        New-Item -ItemType Directory -Force -Path $dir | Out-Null
    }
    if (-not (Test-Path $path)) {
        New-Item -ItemType File -Force -Path $path | Out-Null
    }
}
Write-Output "Folder structure created successfully."
