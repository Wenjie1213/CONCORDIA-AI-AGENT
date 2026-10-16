const fs = require('fs')
const path = require('path')
const { spawnSync, spawn } = require('child_process')

const scenario = process.argv[2] || 'mc_physical_intimidation_v1'
const observerMode = process.env.OBSERVER_MODE || 'observe_only'

const repoRoot = path.resolve(__dirname, '..')
const pythonPath = process.env.PYTHON || path.join(repoRoot, '.venv', 'Scripts', 'python.exe')
const outputPath = path.join(
  repoRoot,
  'experiments',
  'non_verbal_minecraft',
  'replay',
  'out',
  `${scenario}_scenario_playback_${observerMode}.json`
)

function envFlag (name) {
  const value = String(process.env[name] || '').toLowerCase()
  return value === '1' || value === 'true' || value === 'yes'
}

function ensurePython () {
  if (fs.existsSync(pythonPath)) return pythonPath
  return process.env.PYTHON || 'python'
}

function validateApiKey (apiKey) {
  if (!apiKey) return
  if (!/^[\x00-\x7F]+$/.test(apiKey) || apiKey.includes('你的') || apiKey.includes('API key')) {
    console.error('Invalid API key value. Set OPENAI_API_KEY to the real ASCII key, not the placeholder text.')
    console.error('PowerShell example: $env:OPENAI_API_KEY="sk-..."')
    process.exit(1)
  }
}

function compileArgs () {
  const args = [
    '-m',
    'experiments.non_verbal_minecraft.replay.compile_scenario_playback',
    scenario,
    '--observer_mode',
    observerMode,
    '--output',
    outputPath
  ]

  if (observerMode === 'llm_response') {
    args.push('--api_type', process.env.API_TYPE || 'openai')
    args.push('--model_name', process.env.MODEL_NAME || 'gpt-5')

    const apiKey = process.env.API_KEY || process.env.OPENAI_API_KEY
    validateApiKey(apiKey)
    if (apiKey) {
      args.push('--api_key', apiKey)
    }
    if (envFlag('DISABLE_LANGUAGE_MODEL')) {
      args.push('--disable_language_model')
    }
    if (envFlag('USE_DUMMY_EMBEDDER')) {
      args.push('--use_dummy_embedder')
    }
    if (envFlag('INCLUDE_RELATIONSHIP_MEMORIES')) {
      args.push('--include_relationship_memories')
    }
  }

  return args
}

console.log(`Compiling scenario playback for ${scenario} (${observerMode})...`)
if (observerMode === 'llm_response') {
  console.log(`LLM response model: ${process.env.MODEL_NAME || 'gpt-5'}`)
}

const compile = spawnSync(
  ensurePython(),
  compileArgs(),
  {
    cwd: repoRoot,
    stdio: 'inherit',
    shell: false
  }
)

if (compile.status !== 0) {
  process.exitCode = compile.status || 1
  process.exit()
}

console.log(`Starting replay viewer from ${outputPath}`)
const runner = spawn(
  process.execPath,
  [path.join(__dirname, 'replay_runner.js'), outputPath],
  {
    cwd: __dirname,
    stdio: 'inherit',
    shell: false
  }
)

runner.on('exit', code => {
  process.exitCode = code || 0
})

