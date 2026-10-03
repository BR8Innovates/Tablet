import sys; sys.path.insert(0, ".")
from uptab import *
CFG = 1188575596
save("UP_ApiConfig", CFG, [dict(Api="*", Scope="*", Key="MsgNotOwner", Value="Only the maker who created this proposal can change it.")], 113, "wfcfg4")
