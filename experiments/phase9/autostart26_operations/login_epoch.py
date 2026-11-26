"""Read only this process's Windows sign-in time; no credentials are accessed."""
import ctypes
from ctypes import wintypes
from functools import lru_cache
import os
import time


@lru_cache(maxsize=1)
def current_logon_start():
    if os.name!="nt":return None
    class Luid(ctypes.Structure):
        _fields_=[("low",wintypes.DWORD),("high",wintypes.LONG)]
    class Unicode(ctypes.Structure):
        _fields_=[("length",wintypes.USHORT),("maximum",wintypes.USHORT),("buffer",ctypes.c_void_p)]
    class SessionPrefix(ctypes.Structure):
        _fields_=[("size",wintypes.ULONG),("id",Luid),("user",Unicode),("domain",Unicode),("auth",Unicode),
                  ("type",wintypes.ULONG),("session",wintypes.ULONG),("sid",ctypes.c_void_p),("logon_time",ctypes.c_longlong)]
    token=wintypes.HANDLE();data=ctypes.c_void_p()
    kernel=ctypes.WinDLL("kernel32",use_last_error=True);advapi=ctypes.WinDLL("advapi32",use_last_error=True);lsa=ctypes.WinDLL("secur32",use_last_error=True)
    kernel.GetCurrentProcess.restype=wintypes.HANDLE
    kernel.CloseHandle.argtypes=[wintypes.HANDLE]
    advapi.OpenProcessToken.argtypes=[wintypes.HANDLE,wintypes.DWORD,ctypes.POINTER(wintypes.HANDLE)]
    advapi.GetTokenInformation.argtypes=[wintypes.HANDLE,ctypes.c_int,ctypes.c_void_p,wintypes.DWORD,ctypes.POINTER(wintypes.DWORD)]
    lsa.LsaGetLogonSessionData.argtypes=[ctypes.POINTER(Luid),ctypes.POINTER(ctypes.c_void_p)]
    lsa.LsaFreeReturnBuffer.argtypes=[ctypes.c_void_p]
    try:
        if not advapi.OpenProcessToken(kernel.GetCurrentProcess(),8,ctypes.byref(token)):return None
        size=wintypes.DWORD()
        advapi.GetTokenInformation(token,10,None,0,ctypes.byref(size))
        if size.value<16:return None
        stats=ctypes.create_string_buffer(size.value)
        if not advapi.GetTokenInformation(token,10,stats,size,ctypes.byref(size)):return None
        # TOKEN_STATISTICS starts with TokenId, then AuthenticationId (two LUIDs).
        authentication=Luid.from_buffer_copy(stats.raw[8:16])
        if lsa.LsaGetLogonSessionData(ctypes.byref(authentication),ctypes.byref(data))!=0 or not data:return None
        info=ctypes.cast(data,ctypes.POINTER(SessionPrefix)).contents
        if info.size<ctypes.sizeof(SessionPrefix):return None
        result=(info.logon_time-116444736000000000)/10000000
        return result if 0<result<=time.time()+1 else None
    except OSError:return None
    finally:
        if data:lsa.LsaFreeReturnBuffer(data)
        if token:kernel.CloseHandle(token)
