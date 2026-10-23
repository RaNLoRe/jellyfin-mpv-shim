-- Jellyfin queue view for playlistmanager. Only this script's mp table is
-- adapted; mpv's native playlist, other scripts and standalone mpv are untouched.
local M = {}
function M.wrap(real, utils)
    local proxy = setmetatable({}, {__index = real})
    local active = false
    local state = {items = {}}
    local serial, accepted, pending = 0, 0, nil
    local focus, pending_action = nil, nil
    local on_change = function() end
    local random_seeded = false
    local function current_pos()
        for i, item in ipairs(state.items) do
            if item.entry == state.current then return i - 1 end
        end
        return 0
    end
    local function request(action, index, before, order)
        if not active then return end
        if pending and real.get_time() - pending < 5
            and (action == 'refresh' or pending_action ~= 'refresh') then return end
        local item = state.items[(tonumber(index) or -1) + 1]
        if action ~= 'refresh' and not item then return end
        if action == 'remove' and item.entry == state.current then
            real.osd_message('Cannot remove the playing queue item')
            return
        end
        if action ~= 'refresh' and action ~= 'select' and not state.editable then
            real.osd_message('Queue editing is unavailable in SyncPlay')
            return
        end
        focus = (action == "move" or action == "reorder") and item.entry or nil
        serial = serial + 1
        pending, pending_action = real.get_time(), action
        real.commandv('script-message', 'jms-queue', utils.format_json({
            action = action, entry = item and item.entry,
            revision = state.revision, before = before, serial = serial, order = order,
        }))
        return true
    end
    local function property(name)
        if name == 'playlist-count' then return #state.items, true end
        if name == 'playlist-pos' then return current_pos(), true end
        if name == 'playlist' then
            local entries = {}
            for i, item in ipairs(state.items) do
                entries[i] = {filename = 'jellyfin-queue://' .. item.entry,
                    title = item.title, id = item.entry,
                    current = item.entry == state.current,
                    playing = item.entry == state.current}
            end
            return entries, true
        end
        local index, field = name:match('^playlist/(%d+)/(.+)$')
        if index then
            local item = state.items[tonumber(index) + 1]
            if not item then return nil, true end
            if field == 'filename' then return 'jellyfin-queue://' .. item.entry, true end
            if field == 'title' then return item.title, true end
            return nil, true
        end
        return nil, false
    end
    for _, getter in ipairs({'get_property', 'get_property_native', 'get_property_number'}) do
        proxy[getter] = function(name, default)
            if active then
                local value, handled = property(name)
                if handled then
                    if value == nil then return default end
                    if getter == 'get_property' and type(value) ~= 'table' then return tostring(value) end
                    return value
                end
            end
            return real[getter](name, default)
        end
    end
    for _, setter in ipairs({'set_property', 'set_property_native', 'set_property_number'}) do
        proxy[setter] = function(name, value)
            if active and name == 'playlist-pos' then
                request('select', value)
                return
            end
            return real[setter](name, value)
        end
    end
    proxy.commandv = function(command, ...)
        local a, b = ...
        if active then
            if command == 'playlist-next' then request('select', current_pos() + 1); return end
            if command == 'playlist-prev' then request('select', current_pos() - 1); return end
            if command == 'playlist-remove' then request('remove', a); return end
            if command == 'playlist-move' then
                local target = state.items[tonumber(b) + 1]
                request('move', a, target and target.entry)
                return
            end
            if command == 'loadfile' or command == 'playlist-clear' or command == 'playlist-shuffle' then
                real.osd_message('Use Jellyfin to add or replace queue items')
                return
            end
        end
        return real.commandv(command, ...)
    end
    proxy.command = function(command)
        if active and (command == 'write-watch-later-config' or command:match('^playlist%-')) then return end
        return real.command(command)
    end
    local bridge = {}
    function bridge.active() return active end
    function bridge.listen(callback) on_change = callback end
    function bridge.refresh() request('refresh') end
    function bridge.reorder(order)
        return request('reorder', current_pos(), nil, order)
    end
    function bridge.reverse()
        local order = {}
        for i = #state.items, 1, -1 do order[#order + 1] = state.items[i].entry end
        return bridge.reorder(order)
    end
    function bridge.shuffle()
        if not random_seeded then
            math.randomseed(os.time() + math.floor(real.get_time() * 1000))
            random_seeded = true
        end
        local order = {}
        for i, item in ipairs(state.items) do order[i] = item.entry end
        for i = #order, 2, -1 do
            local j = math.random(i)
            order[i], order[j] = order[j], order[i]
        end
        return bridge.reorder(order)
    end
    function bridge.ready()
        if not active then return true end
        if #state.items > 0 then return true end
        request('refresh')
        real.osd_message(state.revision and 'No active Jellyfin queue' or 'Waiting for the Jellyfin queue bridge')
        return false
    end
    function bridge.unsupported()
        if not active then return false end
        real.osd_message('Use Jellyfin for playlist file operations')
        return true
    end
    real.register_script_message('jms-queue-state', function(raw)
        if not active then return end
        local next_state = utils.parse_json(raw)
        if type(next_state) ~= 'table' or type(next_state.items) ~= 'table'
            or type(next_state.serial) ~= 'number' or next_state.serial < serial
            or next_state.serial <= accepted then return end
        for _, item in ipairs(next_state.items) do
            if type(item.entry) ~= 'string' or type(item.title) ~= 'string' then return end
        end
        accepted, pending = next_state.serial, nil
        local previous = state
        next_state.focus, focus = focus, nil
        state = next_state
        on_change(previous, state)
    end)
    local function detect(name)
        local detected = name and name:find('mpv-jellyfin', 1, true) ~= nil or false
        if detected == active then return end
        active, state, pending = detected, {items = {}}, nil
        on_change(nil, state)
        request('refresh')
    end
    -- Observe directly as well: a one-shot broadcast can arrive before this
    -- script registers, depending on script startup order.
    real.observe_property('input-ipc-server', 'string', function(_, name) detect(name) end)
    detect(real.get_property('input-ipc-server', ''))
    return proxy, bridge
end
return M
