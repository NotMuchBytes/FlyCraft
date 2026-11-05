-- Local OBS control. Never sends desktop input or controls another recording.
obs = obslua
local command_file, state_file = "", ""
local token, command, heartbeat = "initial", "idle", 0
local owned, requested, last_token, owned_heartbeat = false, false, "", 0
local record_started, screenshot_taken, previous_state, ever_active = 0, false, "", false
local last_screenshot = 0
local window_class, process_name = "GLFW30", "java.exe"

local function capture_window(capture_token)
    return "FlyCraft Recording " .. capture_token .. ":" .. window_class .. ":" .. process_name
end

local function event(message)
    local file = io.open(state_file .. ".events.log", "a")
    if file then file:write(tostring(os.time()), " ", token, " ", message, "\n"); file:close() end
end

local function poll()
    local file = io.open(command_file, "r")
    if file then
        local next_token, next_command = file:read("*l"), file:read("*l")
        local next_heartbeat, complete = tonumber(file:read("*l")), file:read("*l")
        file:close()
        if next_token and next_command and next_heartbeat and complete == "END" then
            token, command, heartbeat = next_token, next_command, next_heartbeat
        end
    end
    local active = obs.obs_frontend_recording_active()
    local fresh = math.abs(os.time() - heartbeat) < 60
    local source = obs.obs_get_source_by_name("Minecraft only")
    local width, height = 0, 0
    local capture_ok = false
    if source then
        local settings = obs.obs_source_get_settings(source)
        local start_command = command == "start" or command == "start_verified"
        local valid_token = token:match("^[%w_-]+$") ~= nil
        if not active and fresh and start_command and valid_token and obs.obs_source_get_id(source) == "window_capture" then
            local expected = capture_window(token)
            if obs.obs_data_get_string(settings, "window") ~= expected or obs.obs_data_get_int(settings, "method") ~= 2 or obs.obs_data_get_int(settings, "priority") ~= 0 then
                obs.obs_data_set_string(settings, "window", expected)
                obs.obs_data_set_int(settings, "method", 2) -- Windows Graphics Capture, never BitBlt
                obs.obs_data_set_int(settings, "priority", 0) -- exact title, never another window
                obs.obs_data_set_bool(settings, "client_area", true)
                obs.obs_data_set_bool(settings, "capture_audio", false)
                obs.obs_data_set_bool(settings, "cursor", false)
                obs.obs_source_update(source, settings)
                event("capture_configured_wgc_exact_title")
            end
        end
        local capture_token = owned and requested and last_token or token
        capture_ok = obs.obs_source_get_id(source) == "window_capture" and obs.obs_data_get_int(settings, "method") == 2
            and obs.obs_data_get_int(settings, "priority") == 0
            and obs.obs_data_get_string(settings, "window") == capture_window(capture_token)
        obs.obs_data_release(settings)
        width, height = obs.obs_source_get_width(source), obs.obs_source_get_height(source)
        obs.obs_source_release(source)
    end
    if owned and requested and not active and (ever_active or os.time() - record_started > 10) then
        event("recording_became_inactive_or_start_failed")
        owned, requested = false, false
    end
    if (command == "start" or command == "start_verified") and fresh and capture_ok and width > 0 and height > 0 and token ~= last_token and not active then
        last_token, owned_heartbeat = token, heartbeat
        owned, requested, screenshot_taken, ever_active = true, true, false, false
        record_started = os.time()
        last_screenshot = 0
        event("start_requested")
        obs.obs_frontend_recording_start()
    end
    if owned and requested then
        if token == last_token and (command == "start" or command == "start_verified") and fresh then owned_heartbeat = heartbeat end
        if (token == last_token and command == "stop") or os.time() - owned_heartbeat >= 60 or not capture_ok then
            event(not capture_ok and "capture_configuration_changed" or command == "stop" and "stop_requested" or "heartbeat_timeout")
            obs.obs_frontend_recording_stop()
            owned, requested = false, false
        end
    end
    active = obs.obs_frontend_recording_active()
    if active and owned and requested then ever_active = true end
    if active and owned and requested and command ~= "start_verified" and os.time() - record_started >= 3 and os.time() - last_screenshot >= 2 then
        obs.obs_frontend_take_screenshot()
        screenshot_taken = true
        last_screenshot = os.time()
    end
    local state = active and (owned and requested and token == last_token and "recording" or "busy") or
                  (owned and requested and "starting" or "stopped")
    if state ~= previous_state then event("state=" .. state); previous_state = state end
    -- Complete frames avoid Windows delete/rename sharing races. Readers
    -- reject partial writes and retain their previous valid command/status.
    local output = io.open(state_file, "w")
    if output then
        output:write(token, "\n", state, "\n", obs.obs_frontend_get_last_recording() or "", "\n",
                     tostring(width), "\n", tostring(height), "\n", tostring(os.time()), "\n",
                     obs.obs_frontend_get_last_screenshot() or "", "\nEND\n")
        output:close()
    end
end

function script_description()
    return "FlyCraft: Minecraft-only recording, complete-frame handshakes, ownership and a 60-second watchdog."
end
function script_load(settings)
    command_file = obs.obs_data_get_string(settings, "command_file")
    state_file = obs.obs_data_get_string(settings, "state_file")
    local configured_class=obs.obs_data_get_string(settings,"window_class") or ""
    local configured_process=obs.obs_data_get_string(settings,"process_name") or ""
    if configured_class:match("^[%w_.-]+$") then window_class=configured_class end
    if configured_process:match("^[%w_.-]+%.exe$") then process_name=configured_process end
    obs.timer_add(poll, 250)
end
function script_unload()
    obs.timer_remove(poll)
    if owned and requested and obs.obs_frontend_recording_active() then obs.obs_frontend_recording_stop() end
end
