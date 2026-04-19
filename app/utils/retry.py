def retry(func, retries=3):
    for i in range(retries):
        try:
            return func()
        except Exception as e:
            if i == retries - 1:
                return {"error": str(e)}
