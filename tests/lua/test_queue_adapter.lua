-- Run with LuaJIT/Lua 5.1. No player or network is started.
local callbacks, requests, native = {}, {}, {}
local now, ipc = 0, ''
local utils = {format_json = function(v) return v end, parse_json = function(v) return v end}
local real = {
    get_time = function() return now end,
    get_property = function(name, default) if name == 'input-ipc-server' then return ipc end; return 'native' end,
    get_property_number = function() return 99 end,
    get_property_native = function() return {} end,
    set_property = function(...) native[#native+1] = {...} end,
    set_property_native = function(...) native[#native+1] = {...} end,
    set_property_number = function(...) native[#native+1] = {...} end,
    commandv = function(cmd, name, body) if name == 'jms-queue' then requests[#requests+1] = body else native[#native+1] = {cmd,name,body} end end,
    command = function(...) native[#native+1] = {...} end,
    osd_message = function() end,
    register_script_message = function(name, fn) callbacks[name] = fn end,
    observe_property = function(name, kind, fn) callbacks[name] = fn end,
}
local mp, bridge = dofile('contrib/mpv/jellyfin_queue_adapter.lua').wrap(real, utils)
assert(mp.get_property_number('playlist-count') == 99)
mp.commandv('playlist-next', 'weak')
assert(#native == 1 and #requests == 0)
ipc = 'mpv-jellyfin-diagnostic'
callbacks['input-ipc-server']('', ipc)
assert(#requests == 1 and mp.get_property_number('playlist-count') == 0)
local function reply(items, current, revision)
    callbacks['jms-queue-state']({serial=requests[#requests].serial, items=items,
        current=current, revision=revision, editable=true})
end
local items = {{entry='a', title='One'}, {entry='b', title='Two'}, {entry='c', title='One'}}
reply(items, 'a', 'r1')
assert(mp.get_property_number('playlist-count') == 3)
assert(mp.get_property('playlist/2/title') == 'One')
assert(mp.get_property('playlist/2/filename') == 'jellyfin-queue://c')
bridge.refresh() -- a refresh in flight must not swallow Enter
mp.set_property('playlist-pos', 2)
assert(requests[#requests].entry == 'c' and requests[#requests].revision == 'r1')
local n = #requests
mp.commandv('playlist-remove', 1) -- busy: cannot apply a second stale action
assert(#requests == n)
reply(items, 'c', 'r2')
assert(mp.get_property_number('playlist-pos') == 2)
mp.commandv('playlist-move', 0, 2)
assert(requests[#requests].action == 'move' and requests[#requests].before == 'c')
reply(items, 'c', 'r2')
mp.commandv('playlist-remove', 2) -- currently playing
assert(#requests == n + 1)
mp.commandv('playlist-remove', 0)
assert(requests[#requests].entry == 'a')
reply({items[2],items[3]}, 'c', 'r3')
assert(mp.get_property_number('playlist-count') == 2)
mp.commandv('loadfile', 'bad-url')
assert(#native == 1) -- no native queue mutations or playable URLs
callbacks['jms-queue-state']({serial=1, items=items, current='a'})
assert(mp.get_property_number('playlist-count') == 2) -- stale response ignored
bridge.reverse()
assert(requests[#requests].action == 'reorder')
assert(table.concat(requests[#requests].order, ',') == 'c,b')
reply({items[3],items[2]}, 'c', 'r4')
assert(mp.get_property_number('playlist-pos') == 0)
assert(#native == 1)
bridge.shuffle()
local shuffled = requests[#requests].order
assert(#shuffled == 2 and shuffled[1] ~= shuffled[2])
assert((shuffled[1] == 'b' or shuffled[1] == 'c') and (shuffled[2] == 'b' or shuffled[2] == 'c'))
assert(requests[#requests].action == 'reorder' and requests[#requests].entry == 'c')
assert(#native == 1) -- session reorder only; no file/playlist operations
callbacks['input-ipc-server']('', '')
mp.commandv('playlist-next', 'weak')
assert(#native == 2 and mp.get_property_number('playlist-count') == 99)
print('Queue adapter state, duplicate selection, stale actions, removal, move and standalone fallback: PASS')

local tick, loaded, paints = nil, nil, 0
real.add_periodic_timer = function(interval, fn) assert(interval == 1); tick = fn end
real.register_event = function(event, fn) assert(event == 'file-loaded'); loaded = fn end
ipc = 'mpv-jellyfin-osc-test'
local osc, osc_bridge = dofile('contrib/mpv/jellyfin_queue_adapter.lua').osc(real, utils)
osc_bridge.listen(function() paints = paints + 1 end)
assert(requests[#requests].reply_to == 'osc')
assert(requests[#requests].action == 'capabilities' and requests[#requests].serial == nil)
assert(not osc_bridge.active())
assert(osc.get_property_number('playlist-count') == 99)
local probes = #requests
tick()
assert(#requests == probes) -- old shim: no queue polling before negotiation
callbacks['jms-queue-capabilities']({version=99})
assert(not osc_bridge.active())
callbacks['jms-queue-capabilities']({version=1})
assert(osc_bridge.active() and requests[#requests].action == 'refresh')
paints = 0
reply(items, 'a', 'osc1')
assert(paints == 1 and osc.get_property_number('playlist-count') == 3)
assert(osc.get_property('loop-playlist') == 'no')
n = #requests
osc.command('playlist-prev') -- first item: cannot move back
assert(#requests == n)
osc.command('playlist-next')
assert(requests[#requests].entry == 'b' and requests[#requests].reply_to == 'osc')
reply(items, 'b', 'osc2')
osc.command('playlist-prev')
assert(requests[#requests].entry == 'a')
reply(items, 'c', 'osc3')
n = #requests
osc.command('playlist-next') -- last item
assert(#requests == n)
tick()
reply({items[3], items[1]}, 'c', 'osc4')
assert(osc.get_property_number('playlist-count') == 2)
assert(osc.get_property_number('playlist-pos') == 0 and paints == 4)
loaded()
reply({}, nil, 'stopped')
assert(osc.get_property_number('playlist-count') == 0)
osc.command('script-binding select/select-playlist; script-message-to osc osc-hide')
assert(native[#native][2] == 'playlistmanager/showplaylist')
callbacks['input-ipc-server']('', '')
osc.command('playlist-next')
assert(native[#native][1] == 'playlist-next')
print('OSC arrows, queue boundaries, repaint, reorder, stop, picker and standalone fallback: PASS')

-- An old shim routes a capability probe to playlistmanager. Its missing serial
-- must neither repaint nor advance the manager's independent request sequence.
ipc = 'mpv-jellyfin-old-shim'
local manager, manager_bridge = dofile('contrib/mpv/jellyfin_queue_adapter.lua').wrap(real, utils)
reply(items, 'b', 'manager')
callbacks['jms-queue-state']({items={}, revision='old-shim', editable=false})
assert(manager.get_property_number('playlist-pos') == 1)
manager.commandv('playlist-next')
assert(requests[#requests].entry == 'c')
print('Old shim capability reply cannot corrupt playlistmanager: PASS')
