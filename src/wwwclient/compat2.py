ENCODING = "UTF-8"

def asyncio_await(value):
	return value

def asyncio_iscoroutine(value):
	return False

def asyncio_isgenerator(value):
	return False

def asyncio_coroutine(value):
	return value

def ensure_str( t, encoding=ENCODING ):
	return t.encode("utf8") if isinstance (t, unicode) else str(t)

def ensure_str_safe ( t, encoding=ENCODING ):
	return t.encode("utf8", "ignore") if isinstance (t, unicode) else str(t)

def ensure_unicode( t, encoding=ENCODING ):
	return t if isinstance(t, unicode) else str(t).decode(encoding)

def ensure_unicode_safe( t, encoding=ENCODING ):
	return t if isinstance(t, unicode) else str(t).decode(encoding, "ignore")
def ensure_bytes( t, encoding=ENCODING ):
	return t if isinstance(t, bytes) else bytes(t)

def is_string( t ):
	return isinstance(t, unicode) or isinstance(t, str)


# EOF
