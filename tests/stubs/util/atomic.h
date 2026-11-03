#pragma once
#define ATOMIC_RESTORESTATE 0
#define ATOMIC_BLOCK(x) for (bool _once = true; _once; _once = false)
