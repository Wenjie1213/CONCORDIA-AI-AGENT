const fs = require('fs')
const path = require('path')
const mineflayer = require('mineflayer')
const { pathfinder, Movements, goals } = require('mineflayer-pathfinder')
const { mineflayer: mineflayerViewer } = require('prismarine-viewer')
const { Vec3 } = require('vec3')

const { GoalNear } = goals

const replayPath = process.argv[2] || path.join(
  '..',
  'experiments',
  'non_verbal_minecraft',
  'replay',
  'out',
  'physical_intimidation_replay.json'
)

const host = process.env.MC_HOST || 'localhost'
const port = Number(process.env.MC_PORT || 25565)
const auth = process.env.MC_AUTH || 'offline'
const baseReplayY = Number(process.env.BASE_REPLAY_Y || 64)
const skyPlatformY = Number(process.env.SKY_PLATFORM_Y || 100)
const platformBlock = process.env.SKY_PLATFORM_BLOCK || 'smooth_quartz'
const amplifyActions = process.env.AMPLIFY_ACTIONS !== '0'
const viewerMode = process.env.VIEWER_MODE || 'camera'
const viewerBotName = process.env.VIEWER_BOT_NAME || 'ViewerCam'
const viewerDistance = Number(process.env.VIEWER_DISTANCE || 16)
const viewerHeight = Number(process.env.VIEWER_HEIGHT || 1)
const viewerSide = (process.env.VIEWER_SIDE || 'south').toLowerCase()
const viewerFirstPerson = process.env.VIEWER_FIRST_PERSON === '1'
const agentNameLabels = process.env.AGENT_NAME_LABELS !== '0'

const agentLabels = {
  Morgan: { team: 'nv_label_morgan', prefix: '[Morgan] ' },
  Riley: { team: 'nv_label_riley', prefix: '[Riley] ' },
  Casey: { team: 'nv_label_casey', prefix: '[Casey] ' },
  Taylor: { team: 'nv_label_taylor', prefix: '[Taylor] ' },
  Jordan: { team: 'nv_label_jordan', prefix: '[Jordan] ' }
}

function sleep (ms) {
  return new Promise(resolve => setTimeout(resolve, ms))
}

function asVec3 (pos) {
  return new Vec3(pos.x, pos.y, pos.z)
}

function commandPos (pos) {
  return `${Math.round(pos.x)} ${Math.round(pos.y)} ${Math.round(pos.z)}`
}

function teamTextComponent (text) {
  return JSON.stringify({ text, bold: true })
}

function isPosition (value) {
  return value &&
    typeof value === 'object' &&
    typeof value.x === 'number' &&
    typeof value.y === 'number' &&
    typeof value.z === 'number'
}

function shiftPosition (pos, deltaY) {
  if (!isPosition(pos)) return pos
  return { ...pos, y: pos.y + deltaY }
}

function shiftNamedPositions (positions, deltaY) {
  if (!positions) return positions
  for (const [key, value] of Object.entries(positions)) {
    positions[key] = shiftPosition(value, deltaY)
  }
  return positions
}

function applySkyPlatform (replay) {
  const deltaY = skyPlatformY - baseReplayY
  if (!Number.isFinite(deltaY) || deltaY === 0) {
    replay.world.platform = {
      enabled: false,
      base_y: baseReplayY,
      y: skyPlatformY,
      block: platformBlock
    }
    return replay
  }

  if (replay.world.origin) replay.world.origin = shiftPosition(replay.world.origin, deltaY)
  if (replay.world.bounds) {
    replay.world.bounds.min = shiftPosition(replay.world.bounds.min, deltaY)
    replay.world.bounds.max = shiftPosition(replay.world.bounds.max, deltaY)
  }

  for (const spec of Object.values(replay.agents || {})) {
    spec.spawn = shiftPosition(spec.spawn, deltaY)
    spec.look_at = shiftPosition(spec.look_at, deltaY)
  }

  shiftNamedPositions(replay.markers, deltaY)

  for (const block of replay.initial_blocks || []) {
    block.pos = shiftPosition(block.pos, deltaY)
    block.to = shiftPosition(block.to, deltaY)
  }

  for (const item of replay.timeline || []) {
    if (isPosition(item.target)) item.target = shiftPosition(item.target, deltaY)
  }

  replay.world.platform = {
    enabled: true,
    base_y: baseReplayY,
    y: skyPlatformY,
    delta_y: deltaY,
    block: platformBlock
  }
  return replay
}

function platformCenter (replay) {
  const bounds = replay.world.bounds
  return {
    x: Math.round((bounds.min.x + bounds.max.x) / 2),
    y: Math.round((bounds.min.y + bounds.max.y) / 2),
    z: Math.round((bounds.min.z + bounds.max.z) / 2)
  }
}

function viewerCameraPosition (replay) {
  const center = platformCenter(replay)
  const floorY = replay.world.bounds.min.y
  const camera = { x: center.x, y: floorY + viewerHeight, z: center.z + viewerDistance }
  if (viewerSide === 'north') {
    camera.z = center.z - viewerDistance
  } else if (viewerSide === 'east') {
    camera.x = center.x + viewerDistance
    camera.z = center.z
  } else if (viewerSide === 'west') {
    camera.x = center.x - viewerDistance
    camera.z = center.z
  }
  return camera
}

function viewerLookTarget (replay) {
  const center = platformCenter(replay)
  const floorY = replay.world.bounds.min.y
  return {
    x: center.x,
    y: floorY + 2,
    z: center.z
  }
}

async function positionViewerCamera (viewerBot, replay, adminBot) {
  const camera = viewerCameraPosition(replay)
  const target = viewerLookTarget(replay)
  await chatCommand(adminBot, `/gamemode spectator ${viewerBot.username}`, 120)
  await chatCommand(adminBot, `/tp ${viewerBot.username} ${commandPos(camera)}`, 180)
  await viewerBot.lookAt(asVec3(target), true)
  await sleep(300)
}

function resolveTarget (replay, target) {
  if (typeof target === 'string') {
    const marker = replay.markers[target]
    if (!marker) throw new Error(`Unknown marker: ${target}`)
    return marker
  }
  return target
}

function createBot (username) {
  const bot = mineflayer.createBot({ host, port, username, auth })
  bot.loadPlugin(pathfinder)
  return bot
}

async function waitForSpawn (bot) {
  if (bot.entity) return
  await new Promise(resolve => bot.once('spawn', resolve))
}

async function chatCommand (bot, command, delay = 160) {
  bot.chat(command)
  await sleep(delay)
}

async function setupWorld (replay, adminBot, bots) {
  const bounds = replay.world.bounds
  const floorY = bounds.min.y
  await chatCommand(adminBot, '/time set day')
  await chatCommand(adminBot, '/weather clear')
  await chatCommand(
    adminBot,
    `/fill ${commandPos(bounds.min)} ${commandPos(bounds.max)} air`
  )
  await chatCommand(
    adminBot,
    `/fill ${bounds.min.x} ${floorY} ${bounds.min.z} ${bounds.max.x} ${floorY} ${bounds.max.z} ${platformBlock}`
  )

  for (const block of replay.initial_blocks) {
    const start = block.marker ? replay.markers[block.marker] : block.pos
    const end = block.to || start
    await chatCommand(
      adminBot,
      `/fill ${commandPos(start)} ${commandPos(end)} ${block.block}`
    )
  }

  for (const [name, spec] of Object.entries(replay.agents)) {
    const spawn = spec.spawn
    await chatCommand(adminBot, `/tp ${name} ${commandPos(spawn)}`)
    if (agentNameLabels && agentLabels[name]) {
      const label = agentLabels[name]
      await chatCommand(adminBot, `/team remove ${label.team}`, 60)
      await chatCommand(adminBot, `/team add ${label.team}`, 60)
      await chatCommand(adminBot, `/team modify ${label.team} nametagVisibility always`, 60)
      await chatCommand(adminBot, `/team modify ${label.team} prefix ${teamTextComponent(label.prefix)}`, 60)
      await chatCommand(adminBot, `/team join ${label.team} ${name}`, 60)
    }
    const bot = bots[name]
    if (bot && spec.look_at) {
      await bot.lookAt(asVec3(spec.look_at).offset(0, 1.4, 0), true)
    }
  }
}

async function gotoTarget (bot, replay, target, range = 1, sprint = false) {
  const pos = resolveTarget(replay, target)
  const movements = new Movements(bot)
  movements.canDig = false
  movements.allow1by1towers = false
  bot.pathfinder.setMovements(movements)
  if (sprint) bot.setControlState('sprint', true)
  try {
    await bot.pathfinder.goto(new GoalNear(pos.x, pos.y, pos.z, range))
  } finally {
    bot.setControlState('sprint', false)
  }
}

async function lookAtAgent (bot, bots, target) {
  const other = bots[target]
  if (!other || !other.entity) return
  await bot.lookAt(other.entity.position.offset(0, 1.5, 0), true)
}

async function lookAtTarget (bot, replay, target) {
  const pos = resolveTarget(replay, target)
  await bot.lookAt(asVec3(pos).offset(0.5, 0.7, 0.5), true)
}

async function pulseSneak (bot, repeats = 2) {
  for (let i = 0; i < repeats; i++) {
    bot.setControlState('sneak', true)
    await sleep(220)
    bot.setControlState('sneak', false)
    await sleep(180)
  }
}

async function jumpPulse (bot, repeats = 1) {
  for (let i = 0; i < repeats; i++) {
    bot.setControlState('jump', true)
    await sleep(260)
    bot.setControlState('jump', false)
    await sleep(220)
  }
}

async function visibleGesture (bot, repeats = 3) {
  const count = amplifyActions ? Math.max(repeats, 3) : repeats
  for (let i = 0; i < count; i++) {
    bot.swingArm(i % 2 === 0 ? 'right' : 'left', true)
    if (amplifyActions && i % 2 === 0) bot.setControlState('sneak', true)
    await sleep(230)
    bot.setControlState('sneak', false)
    await sleep(180)
  }
}

async function backAwayFromAgent (bot, bots, target, durationMs = 900) {
  await lookAtAgent(bot, bots, target)
  bot.setControlState('back', true)
  await sleep(durationMs)
  bot.setControlState('back', false)
}

async function turnAway (bot) {
  if (!bot.entity) return
  await bot.look(bot.entity.yaw + Math.PI, 0, true)
  await sleep(450)
}

async function showParticle (adminBot, pos, particle = 'minecraft:happy_villager') {
  await chatCommand(
    adminBot,
    `/particle ${particle} ${Math.round(pos.x)} ${Math.round(pos.y + 1)} ${Math.round(pos.z)} 0.35 0.45 0.35 0.01 8`,
    100
  )
}

async function runCommand (cmd, replay, bots, adminBot) {
  const bot = bots[cmd.agent]
  if (!bot) throw new Error(`Unknown agent: ${cmd.agent}`)

  if (cmd.cmd === 'goto') {
    await gotoTarget(bot, replay, cmd.target, cmd.range || 1, Boolean(cmd.sprint))
    if (amplifyActions && cmd.emphasis) await visibleGesture(bot, 1)
    return
  }

  if (cmd.cmd === 'sprint_goto') {
    await gotoTarget(bot, replay, cmd.target, cmd.range || 1, true)
    if (amplifyActions) await jumpPulse(bot, 1)
    return
  }

  if (cmd.cmd === 'look_at_agent') {
    await lookAtAgent(bot, bots, cmd.target)
    return
  }

  if (cmd.cmd === 'look_at_block') {
    await lookAtTarget(bot, replay, cmd.target)
    return
  }

  if (cmd.cmd === 'swing_arm') {
    const baseRepeat = cmd.repeat || 1
    const repeat = amplifyActions ? Math.max(baseRepeat, cmd.emphasis === 'high' ? 6 : 3) : baseRepeat
    await visibleGesture(bot, repeat)
    return
  }

  if (cmd.cmd === 'emote_signal') {
    if (cmd.target_agent) await lookAtAgent(bot, bots, cmd.target_agent)
    if (cmd.target) await lookAtTarget(bot, replay, cmd.target)
    await visibleGesture(bot, cmd.repeat || 4)
    if (cmd.jump || amplifyActions) await jumpPulse(bot, 1)
    return
  }

  if (cmd.cmd === 'jump') {
    await jumpPulse(bot, cmd.repeat || 1)
    return
  }

  if (cmd.cmd === 'back_away') {
    await backAwayFromAgent(bot, bots, cmd.target_agent || 'Morgan', Number(cmd.duration_ms || 900))
    return
  }

  if (cmd.cmd === 'turn_away') {
    await turnAway(bot)
    return
  }

  if (cmd.cmd === 'sneak') {
    if (cmd.pulse || (amplifyActions && cmd.state)) {
      await pulseSneak(bot, cmd.repeat || 2)
    } else {
      bot.setControlState('sneak', Boolean(cmd.state))
      await sleep(350)
    }
    return
  }

  if (cmd.cmd === 'stand') {
    await sleep(Number(cmd.ticks || 20) * 50)
    return
  }

  if (cmd.cmd === 'place_block') {
    const pos = resolveTarget(replay, cmd.target)
    await gotoTarget(bot, replay, pos, 2)
    await lookAtTarget(bot, replay, pos)
    await visibleGesture(bot, 1)
    await chatCommand(adminBot, `/setblock ${commandPos(pos)} ${cmd.block}`)
    if (amplifyActions) await showParticle(adminBot, pos, 'minecraft:happy_villager')
    await sleep(250)
    return
  }

  if (cmd.cmd === 'dig_block') {
    const pos = resolveTarget(replay, cmd.target)
    await gotoTarget(bot, replay, pos, 2)
    await lookAtTarget(bot, replay, pos)
    await visibleGesture(bot, 2)
    await chatCommand(adminBot, `/setblock ${commandPos(pos)} air`)
    if (amplifyActions) await showParticle(adminBot, pos, 'minecraft:crit')
    await sleep(250)
    return
  }

  if (cmd.cmd === 'place_marker') {
    const pos = resolveTarget(replay, cmd.target)
    await gotoTarget(bot, replay, pos, 2)
    await lookAtTarget(bot, replay, pos)
    await visibleGesture(bot, 1)
    await chatCommand(adminBot, `/setblock ${commandPos(pos)} ${cmd.block || 'yellow_wool'}`)
    if (amplifyActions) await showParticle(adminBot, pos, 'minecraft:happy_villager')
    await sleep(250)
    return
  }

  throw new Error(`Unsupported replay command: ${cmd.cmd}`)
}

async function main () {
  const replay = applySkyPlatform(JSON.parse(fs.readFileSync(replayPath, 'utf8')))
  const agentNames = Object.keys(replay.agents)
  const bots = {}

  console.log(`Connecting ${agentNames.length} experiment bots to ${host}:${port}...`)
  console.log(`Sky platform: y=${skyPlatformY}, block=${platformBlock}`)
  console.log(`Amplified actions: ${amplifyActions ? 'on' : 'off'}`)
  console.log(`Viewer mode: ${viewerMode}`)
  console.log(`Viewer camera: side=${viewerSide}, distance=${viewerDistance}, height=${viewerHeight}, firstPerson=${viewerFirstPerson ? 'on' : 'off'}`)
  console.log(`Agent name labels: ${agentNameLabels ? 'on' : 'off'}`)
  for (const name of agentNames) {
    bots[name] = createBot(name)
  }
  let cameraBot = null
  if (viewerMode === 'camera') {
    cameraBot = createBot(viewerBotName)
  }

  await Promise.all([...Object.values(bots), ...(cameraBot ? [cameraBot] : [])].map(waitForSpawn))
  console.log('All bots spawned.')

  const viewerAgent = replay.world.viewer.agent || agentNames[0]
  const viewerBot = cameraBot || bots[viewerAgent]
  mineflayerViewer(viewerBot, {
    port: replay.world.viewer.port || 3000,
    firstPerson: viewerFirstPerson,
    viewDistance: replay.world.viewer.viewDistance || 6
  })
  console.log(`Viewer started on http://localhost:${replay.world.viewer.port || 3000}`)

  const adminBot = bots[agentNames[0]]
  console.log('Setting up deterministic sky platform. The admin bot must be allowed to run /fill, /setblock, and /tp.')
  await setupWorld(replay, adminBot, bots)
  if (cameraBot) {
    await positionViewerCamera(cameraBot, replay, adminBot)
    console.log(`Viewer camera positioned at ${commandPos(viewerCameraPosition(replay))}, eye-level on-platform view.`)
  }
  await sleep(1000)

  console.log(`Running replay: ${replay.scenario_id} / ${replay.run_id || 'unknown run'}`)
  const timeline = [...replay.timeline].sort((a, b) => a.t - b.t)
  let currentT = 0
  for (const cmd of timeline) {
    const wait = Math.max(0, cmd.t - currentT)
    if (wait > 0) await sleep(wait * 50)
    currentT = cmd.t
    console.log(`[t=${cmd.t}] ${cmd.agent}.${cmd.cmd}`)
    await runCommand(cmd, replay, bots, adminBot)
  }

  console.log('Replay finished. Keep this process open while viewing the scene.')
}

main().catch(err => {
  console.error(err)
  process.exitCode = 1
})
