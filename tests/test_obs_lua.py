"""Run the actual OBS Lua script against a headless frontend stub, using OBS's existing Lua DLL."""
import ctypes
import json
import os
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
LUA = Path(os.environ.get("PROGRAMFILES", "C:/Program Files")) / "obs-studio/bin/64bit/lua51.dll"


@unittest.skipUnless(os.name == "nt" and LUA.is_file(), "Installed OBS Lua runtime unavailable")
class ObsLuaTests(unittest.TestCase):
    def test_recording_ownership_partial_frames_async_start_and_watchdog(self):
        library = ctypes.CDLL(str(LUA))
        library.luaL_newstate.restype = ctypes.c_void_p
        library.luaL_openlibs.argtypes = [ctypes.c_void_p]
        library.luaL_loadstring.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
        library.luaL_loadstring.restype = ctypes.c_int
        library.lua_pcall.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_int, ctypes.c_int]
        library.lua_pcall.restype = ctypes.c_int
        library.lua_tolstring.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p]
        library.lua_tolstring.restype = ctypes.c_char_p
        library.lua_close.argtypes = [ctypes.c_void_p]
        state = library.luaL_newstate()
        self.assertTrue(state)
        try:
            library.luaL_openlibs(state)
            with tempfile.TemporaryDirectory() as directory:
                command = json.dumps((Path(directory) / "command.txt").as_posix())
                output = json.dumps((Path(directory) / "state.txt").as_posix())
                stub = """
clock, active, starts, stops = 100000, false, 0, 0
os.time = function() return clock end
obslua = {
 obs_frontend_recording_active=function() return active end,
 obs_frontend_recording_start=function() starts=starts+1 end,
 obs_frontend_recording_stop=function() stops=stops+1; active=false end,
 obs_get_source_by_name=function() return {} end,
 obs_source_get_width=function() return 854 end,
 obs_source_get_height=function() return 480 end,
 obs_source_release=function() end,
 obs_frontend_take_screenshot=function() end,
 obs_frontend_get_last_recording=function() return 'mock.mp4' end,
 obs_frontend_get_last_screenshot=function() return '' end,
 obs_data_get_string=function(settings,key) return settings[key] end,
 timer_add=function(callback) poller=callback end,
 timer_remove=function() end
}
"""
                cases = f"""
command_path, state_path = {command}, {output}
script_load({{command_file=command_path, state_file=state_path}})
function write_command(token, command, complete)
 local f=assert(io.open(command_path,'w'))
 f:write(token,'\\n',command,'\\n',tostring(clock),'\\n', complete and 'END\\n' or '')
 f:close()
end
function status()
 local f=assert(io.open(state_path,'r')); f:read('*l'); local s=f:read('*l'); f:close(); return s
end
write_command('A','start',true); poller()
assert(starts==1 and status()=='starting','asynchronous start must retain ownership')
poller(); assert(starts==1 and stops==0)
active=true; poller(); assert(status()=='recording')
write_command('A','stop',false); poller(); assert(stops==0,'ignore partial stop')
os.remove(command_path); poller(); assert(stops==0,'missing command retains valid heartbeat')
write_command('A','stop',true); poller(); assert(stops==1 and status()=='stopped')
active=true; clock=clock+61; poller()
assert(stops==1 and status()=='busy','never stop an external recording')
write_command('B','start',true); poller(); assert(starts==1 and status()=='busy')
active=false; poller(); assert(starts==2 and status()=='starting')
active=true; poller(); assert(status()=='recording')
write_command('A','stop',true); poller(); assert(stops==1,'old token cannot stop B')
write_command('B','start',true); poller(); clock=clock+61; poller()
assert(stops==2 and not active,'owned recording stops when heartbeat expires')
active=true; script_unload(); assert(stops==2,'unload must preserve external recording')
"""
                code = stub + (ROOT / "tools/obs_recording.lua").read_text(encoding="utf-8") + cases
                error = library.luaL_loadstring(state, code.encode())
                if not error:
                    error = library.lua_pcall(state, 0, 0, 0)
                if error:
                    self.fail(library.lua_tolstring(state, -1, None).decode())
        finally:
            library.lua_close(state)


if __name__ == "__main__":
    unittest.main()
