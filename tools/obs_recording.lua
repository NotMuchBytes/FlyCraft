-- Local, bounded recording control using OBS's frontend API. No hotkeys or UI input.
obs = obslua
local command_file, state_file = "", ""
local owned, requested, last_token = false, false, ""
local record_started, screenshot_taken = 0, false

local function poll()
    local file = io.open(command_file, "r")
    local token, command, heartbeat = "", "idle", 0
    if file then
        token = file:read("*l") or ""
        command = file:read("*l") or "idle"
        heartbeat = tonumber(file:read("*l")) or 0
        file:close()
    end
    local active = obs.obs_frontend_recording_active()
    local fresh = math.abs(os.time() - heartbeat) < 60
    local source = obs.obs_get_source_by_name("Minecraft only")
    local width, height = 0, 0
    if source then
        width = obs.obs_source_get_width(source)
        height = obs.obs_source_get_height(source)
        obs.obs_source_release(source)
    end
    if command == "start" and fresh and width > 0 and height > 0 then
        if token ~= last_token and not active then
            last_token = token
            owned, requested = true, true
            record_started, screenshot_taken = os.time(), false
            obs.obs_frontend_recording_start()
        end
    elseif owned and (command == "stop" or not fresh) then
        obs.obs_frontend_recording_stop()
        requested = false
    end
    active = obs.obs_frontend_recording_active()
    if active and owned and not screenshot_taken and os.time() - record_started >= 3 then
        local captured = obs.obs_get_source_by_name("Minecraft only")
        if captured then
            obs.obs_frontend_take_source_screenshot(captured)
            obs.obs_source_release(captured)
        end
        screenshot_taken = true
    end
    local state = active and (owned and "recording" or "busy") or (requested and "starting" or "stopped")
    local output = io.open(state_file .. ".tmp", "w")
    if output then
        output:write(token, "\n", state, "\n", obs.obs_frontend_get_last_recording() or "", "\n",
                     tostring(width), "\n", tostring(height), "\n", tostring(os.time()), "\n",
                     obs.obs_frontend_get_last_screenshot() or "", "\n")
        output:close()
        os.remove(state_file)
        os.rename(state_file .. ".tmp", state_file)
    end
end

function script_description()
    return "FlyCraft: Minecraft-only recording with local confirmation and a 60-second supervisor watchdog."
end
function script_load(settings)
    command_file = obs.obs_data_get_string(settings, "command_file")
    state_file = obs.obs_data_get_string(settings, "state_file")
    obs.timer_add(poll, 250)
end
function script_unload()
    obs.timer_remove(poll)
    if owned and obs.obs_frontend_recording_active() then obs.obs_frontend_recording_stop() end
end
