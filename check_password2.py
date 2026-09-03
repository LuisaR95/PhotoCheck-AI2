from auth.security import hash_password, verify_password

nuevo_hash = hash_password("1234")
print("Hash generado ahora:", nuevo_hash)

resultado = verify_password("1234", nuevo_hash)
print("¿Verifica correctamente un hash recién creado?:", resultado)
