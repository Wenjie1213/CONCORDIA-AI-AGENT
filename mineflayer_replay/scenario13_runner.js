const fs = require('fs')
const path = require('path')
const { exec } = require('child_process')
const mineflayer = require('mineflayer')
const { pathfinder, Movements, goals } = require('mineflayer-pathfinder')
const Vec3 = require('vec3').Vec3

const { GoalNear } = goals

function getArg(name, fallback) {
  const prefix = `--${name}=`
  const match = process.argv.find((arg) => arg.startsWith(prefix))
  return match ? match.slice(prefix.length) : fallback
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

const defaultActionsFile = path.resolve(
  __dirname,
  '..',
  'concordia',
  'results',
  'nonverbal_abuse_llm',
  'contract_test_gpt5',
  'scenario_13',
  'run_1',
  'humiliating_visual_structure_20260728_235230_actions.json'
)

const host = getArg('host', 'localhost')
const port = Number(getArg('port', '25565'))
const version = getArg('version', '1.20.1')
const actionsFile = path.resolve(getArg('actions', defaultActionsFile))
const enableViewer = getArg('viewer', 'true') !== 'false'
const autoOpenViewer = getArg('open-viewer', 'true') !== 'false'
const startDelaySeconds = Number(getArg('start-delay-seconds', '15'))
const holdSeconds = Number(getArg('hold-seconds', '120'))
const arenaX = Number(getArg('arena-x', '0'))
const arenaY = Number(getArg('arena-y', '90'))
const arenaZ = Number(getArg('arena-z', '0'))

const rawActions = JSON.parse(fs.readFileSync(actionsFile, 'utf8'))
const schemas = rawActions.map((entry) => entry.action_schema).filter(Boolean)
const agentNames = ['Riley', 'Morgan', 'Casey', 'Taylor', 'Jordan']
const bots = {}
const schemaByAgent = Object.fromEntries(schemas.map((schema) => [schema.agent_id || schema.agent_name, schema]))

function createAgent(username) {
  const bot = mineflayer.createBot({
    host,
    port,
    username,
    auth: 'offline',
    version,
  })

  bot.loadPlugin(pathfinder)

  bot.once('spawn', () => {
    bot.pathfinder.setMovements(new Movements(bot))
    console.log(`${username} spawned at ${bot.entity.position}`)
  })

  bot.on('kicked', (reason) => {
    console.log(`${username} kicked:`, reason)
  })

  bot.on('error', (error) => {
    console.error(`${username} error:`, error.message)
  })

  return bot
}

function waitForSpawn(bot) {
  if (bot.entity) return Promise.resolve()
  return new Promise((resolve) => bot.once('spawn', resolve))
}

async function gotoNear(bot, position, range = 1) {
  try {
    await bot.pathfinder.goto(new GoalNear(position.x, position.y, position.z, range))
  } catch (error) {
    console.log(`${bot.username} pathfinder fallback: ${error.message}`)
    bot.setControlState('forward', true)
    await sleep(1000)
    bot.setControlState('forward', false)
  }
}

async function lookAt(bot, position) {
  if (!bot?.entity) return
  await bot.lookAt(position.offset(0, 1.2, 0), true).catch(() => {})
}

async function visibleGesture(bot, focusPosition, repeats = 3) {
  if (!bot?.entity) return
  for (let i = 0; i < repeats; i++) {
    await bot.lookAt(focusPosition.offset(i % 2 === 0 ? -0.8 : 0.8, 1.4, 0), true).catch(() => {})
    bot.swingArm(i % 2 === 0 ? 'right' : 'left')
    bot.setControlState('sneak', true)
    await sleep(250)
    bot.setControlState('sneak', false)
    await sleep(300)
  }
}

function runCommand(bot, command) {
  bot.chat(command)
}

async function setupArena(operator, origin) {
  console.log(`Creating flat demo arena around ${origin}.`)
  runCommand(operator, '/time set noon')
  await sleep(200)
  runCommand(operator, '/weather clear')
  await sleep(200)
  runCommand(operator, `/fill ${origin.x - 18} ${origin.y - 1} ${origin.z - 18} ${origin.x + 18} ${origin.y - 1} ${origin.z + 18} smooth_stone`)
  await sleep(500)
  runCommand(operator, `/fill ${origin.x - 18} ${origin.y} ${origin.z - 18} ${origin.x + 18} ${origin.y + 12} ${origin.z + 18} air`)
  await sleep(500)
  runCommand(operator, `/fill ${origin.x - 6} ${origin.y - 1} ${origin.z - 2} ${origin.x + 7} ${origin.y - 1} ${origin.z + 2} light_gray_concrete`)
  await sleep(500)
  runCommand(operator, `/tp Riley ${origin.x - 6} ${origin.y} ${origin.z}`)
  await sleep(200)
  runCommand(operator, `/tp Morgan ${origin.x + 1} ${origin.y} ${origin.z - 5}`)
  await sleep(200)
  runCommand(operator, `/tp Casey ${origin.x - 4} ${origin.y} ${origin.z + 5}`)
  await sleep(200)
  runCommand(operator, `/tp Taylor ${origin.x - 8} ${origin.y} ${origin.z + 6}`)
  await sleep(200)
  runCommand(operator, `/tp Jordan ${origin.x - 3} ${origin.y} ${origin.z - 5}`)
  await sleep(1500)
}

async function setBlock(bot, position, blockName) {
  runCommand(bot, `/setblock ${position.x} ${position.y} ${position.z} ${blockName}`)
  await sleep(180)
  return true
}

async function performVisibleBlockEdit(bot, position, blockName) {
  const standPosition = position.offset(0, 0, -3)
  await gotoNear(bot, standPosition, 1)
  await lookAt(bot, position)
  await visibleGesture(bot, position, 1)
  console.log(`${bot.username} sets ${blockName} at ${position}`)
  const ok = await setBlock(bot, position, blockName)
  await sleep(250)
  return ok
}

function defaultMockingFaceBlocks() {
  return [
    { offset: [0, 0, 0], block_type: 'oak_planks' },
    { offset: [0, 1, 0], block_type: 'oak_planks' },
    { offset: [0, 2, 0], block_type: 'oak_planks' },
    { offset: [0, 3, 0], block_type: 'oak_planks' },
    { offset: [4, 0, 0], block_type: 'oak_planks' },
    { offset: [4, 1, 0], block_type: 'oak_planks' },
    { offset: [4, 2, 0], block_type: 'oak_planks' },
    { offset: [4, 3, 0], block_type: 'oak_planks' },
    { offset: [1, 3, 0], block_type: 'oak_planks' },
    { offset: [2, 3, 0], block_type: 'oak_planks' },
    { offset: [3, 3, 0], block_type: 'oak_planks' },
    { offset: [1, 2, 0], block_type: 'white_wool' },
    { offset: [3, 2, 0], block_type: 'white_wool' },
    { offset: [1, 1, 0], block_type: 'black_wool' },
    { offset: [2, 1, 0], block_type: 'red_wool' },
    { offset: [3, 1, 0], block_type: 'black_wool' },
    { offset: [2, 0, 0], block_type: 'red_wool' },
  ]
}

function blocksFromMorganSchema() {
  const execution = schemaByAgent.Morgan?.execution || {}
  const blocks = execution.blocks
  if (Array.isArray(blocks) && blocks.length > 0) return blocks
  return defaultMockingFaceBlocks()
}

async function buildHumiliatingFrame(morgan, origin) {
  console.log(`Morgan begins building visible humiliating structure near ${origin}`)
  const placements = blocksFromMorganSchema()

  let placed = 0
  for (const placement of placements) {
    const [x, y, z] = placement.offset || [0, 0, 0]
    const blockName = placement.block_type || 'oak_planks'
    const ok = await performVisibleBlockEdit(morgan, origin.offset(x, y, z), blockName)
    if (ok) placed += 1
  }

  console.log(`Morgan placed ${placed}/${placements.length} blocks.`)
}

async function setMarker(bot, position, blockName) {
  await performVisibleBlockEdit(bot, position, blockName)
}

async function removeFaceBlock(bot, structureOrigin, offset) {
  const position = structureOrigin.offset(offset[0], offset[1], offset[2])
  await performVisibleBlockEdit(bot, position, 'air')
}

async function performRileyReaction(riley, jordan, structureOrigin) {
  console.log('Riley reacts gently: creates distance and moves toward support.')
  await lookAt(riley, structureOrigin)
  await gotoNear(riley, structureOrigin.offset(-5, 0, 5), 1)
  if (jordan?.entity) await lookAt(riley, jordan.entity.position)
}

async function performCaseyReaction(casey, morgan, structureOrigin) {
  console.log('Casey reacts assertively: approaches Morgan, gestures, and holds ground near the build site.')
  const morganPosition = morgan?.entity?.position
  const challengePosition = morganPosition
    ? morganPosition.floored().offset(1, 0, 1)
    : structureOrigin.offset(3, 0, -3)
  await gotoNear(casey, challengePosition, 1)
  if (morgan?.entity) await visibleGesture(casey, morgan.entity.position, 4)
  await gotoNear(casey, structureOrigin.offset(2, 0, -2), 1)
  if (morgan?.entity) await lookAt(casey, morgan.entity.position)
}

async function performTaylorReaction(taylor, structureOrigin) {
  console.log('Taylor reacts cautiously: takes a side witness position.')
  await gotoNear(taylor, structureOrigin.offset(-6, 0, 4), 1)
  await lookAt(taylor, structureOrigin)
}

async function performJordanReaction(jordan, riley, structureOrigin) {
  console.log('Jordan reacts actively: moves into a body-buffer position and places a visible respect marker.')
  await gotoNear(jordan, structureOrigin.offset(-1, 0, -3), 1)
  await lookAt(jordan, structureOrigin)
  await visibleGesture(jordan, structureOrigin, 3)
  const bufferOffsets = [
    [-2, 0, -1],
    [-1, 0, -1],
    [0, 0, -1],
  ]
  for (const offset of bufferOffsets) {
    await setMarker(jordan, structureOrigin.offset(offset[0], offset[1], offset[2]), 'white_wool')
  }
  await gotoNear(jordan, structureOrigin.offset(-3, 0, 1), 1)
  if (riley?.entity) await lookAt(jordan, riley.entity.position)
}

async function runScenario13() {
  console.log(`Reading actions from: ${actionsFile}`)
  console.log('Loaded action schemas:', schemas.map((s) => `${s.agent_id}:${s.action_type}`).join(', '))

  for (const name of agentNames) {
    bots[name] = createAgent(name)
  }

  await Promise.all(agentNames.map((name) => waitForSpawn(bots[name])))
  await sleep(2000)

  const riley = bots.Riley
  const morgan = bots.Morgan
  const casey = bots.Casey
  const taylor = bots.Taylor
  const jordan = bots.Jordan
  const arenaOrigin = new Vec3(arenaX, arenaY, arenaZ)
  const structureOrigin = arenaOrigin.offset(2, 0, 0)

  if (enableViewer) {
    try {
      const { mineflayer: viewer } = require('prismarine-viewer')
      viewer(riley, { port: 3007, firstPerson: false })
      console.log('Viewer ready: http://localhost:3007')
      if (autoOpenViewer) exec('start http://localhost:3007')
    } catch (error) {
      console.log(`Viewer disabled: ${error.message}`)
    }
  }

  await setupArena(morgan, arenaOrigin)
  console.log('If the arena did not appear, type "op Morgan" in the server console and rerun.')

  await Promise.allSettled([
    lookAt(riley, structureOrigin),
    lookAt(casey, structureOrigin),
    lookAt(taylor, structureOrigin),
    lookAt(jordan, structureOrigin),
  ])

  if (startDelaySeconds > 0) {
    console.log(`Waiting ${startDelaySeconds} seconds before Morgan builds. Open viewer now.`)
    await sleep(startDelaySeconds * 1000)
  }

  await buildHumiliatingFrame(morgan, structureOrigin)

  await Promise.allSettled([
    performRileyReaction(riley, jordan, structureOrigin),
    performTaylorReaction(taylor, structureOrigin),
  ])
  await sleep(1000)
  await performCaseyReaction(casey, morgan, structureOrigin)
  await sleep(1000)
  await performJordanReaction(jordan, riley, structureOrigin)

  const lookTimer = setInterval(() => {
    for (const name of ['Riley', 'Casey', 'Taylor', 'Jordan']) {
      lookAt(bots[name], structureOrigin)
    }
  }, 1500)

  console.log(`Holding scene for ${holdSeconds} seconds.`)
  await sleep(holdSeconds * 1000)
  clearInterval(lookTimer)
  console.log('Scenario 13 visual demo complete.')
}

runScenario13().catch((error) => {
  console.error('Scenario 13 runner failed:', error)
})
