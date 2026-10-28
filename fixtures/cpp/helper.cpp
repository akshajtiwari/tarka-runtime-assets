#include <zlib.h>
unsigned long compressedCapacity() { return compressBound(32); }
