const fs = require('fs')
const fs = require('fs')
const path = require('path')
const { spawnSync, spawn } = require('child_process')

function getArg (name, fallback) {
  const prefix = `--${name}=`
  const match = process.argv.find(arg => arg.startsWith(prefix))
  return match ? match.slice(prefix.length) : fallback
}

const scenario = process.argv[2] && !process.argv[2].startsWith('--')
  ? process.argv[2]
  : getArg('scenario', 'mc_chest_access_denial_v1')
const repoRoot = path.resolve(__dirname, '..')
const pythonPath = process.env.PYTHON || path.join(repoRoot, '.venv', 'Scripts', 'python.exe')
const outputDir = path.join(
  repoRoot,
  'experiments',
  'non_verbal_minecraft',
  'replay',
  'out',
  'best_transferable_runs'
)
const manifestPath = path.join(outputDir, 'best_replay_manifest.json')

function ensurePython () {
  if (fs.existsSync(pythonPath)) return pythonPath
  return process.env.PYTHON || 'python'
}

function compileBestRuns () {
  const args = [
    '-m',
    'experiments.non_verbal_minecraft.replay.compile_best_transferable_replays',
    '--output_dir',
    outputDir
  ]
  const compile = spawnSync(ensurePython(), args, {
    cwd: repoRoot,
    stdio: 'inherit',
    shell: false
  })
  if (compile.status !== 0) {
    process.exitCode = compile.status || 1
    process.exit()
  }
}

function loadManifest () {
  if (!fs.existsSync(manifestPath) || getArg('refresh', 'false') === 'true') {
    compileBestRuns()
  }
  return JSON.parse(fs.readFileSync(manifestPath, 'utf8')).runs
}

function printList (runs) {
  console.log('Available best transferable replays:')
  for (const row of runs) {
    console.log(`${row.scenario_id}  score=${row.scientific_transferability_score}  run=${row.run_id}`)
  }
}

const runs = loadManifest()
if (process.argv.includes('--list')) {
  printList(runs)
  process.exit(0)
}

const selected = runs.find(row => row.scenario_id === scenario)
if (!selected) {
  console.error(`No best replay found for scenario: ${scenario}`)
  printList(runs)
  process.exit(1)
}

const replayPath = path.resolve(repoRoot, selected.replay_path)
console.log(`Selected best transferable replay:`)
console.log(`  scenario: ${selected.scenario_id}`)
console.log(`  run:      ${selected.run_id}`)
console.log(`  score:    ${selected.scientific_transferability_score}`)
console.log(`  file:     ${replayPath}`)

const runner = spawn(
  process.execPath,
  [path.join(__dirname, 'replay_runner.js'), replayPath],
  {
    cwd: __dirname,
    stdio: 'inherit',
    shell: false
  }
)

runner.on('exit', code => {
  process.exitCode = code || 0
})
