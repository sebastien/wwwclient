import asyncio, types

ENCODING = "UTF-8"

async def asyncio_await(value):
	return await value

asyncio_coroutine   = asyncio.coroutine
asyncio_iscoroutine = asyncio.iscoroutine

def asyncio_isgenerator(value):
	return isinstance(value, types.AsyncGeneratorType)

unicode = str
long    = int

def ensure_str( t, encoding=ENCODING ):
	return t if isinstance(t, str) else str(t, encoding)

def ensure_str_safe ( t, encoding=ENCODING ):
	return t.encode("utf8", "ignore") if isinstance (t, unicode) else str(t)

def ensure_unicode( t, encoding=ENCODING ):
	return t if isinstance(t, str) else str(t, encoding)

def ensure_unicode_safe( t, encoding=ENCODING ):
	return t if isinstance(t, str) else str(t, encoding, "ignore")

def ensure_bytes( t, encoding=ENCODING ):
	return t if isinstance(t, bytes) else bytes(t, encoding)

def is_string( t ):
	return isinstance(t, str)

# EOF
