from auth.security import verify_password

hash_guardado = "$2b$12$xXqqO2YO0hAQXuqmceH2Z.fLXKlmeIVkW1w2p1Zego.gvaiGomzfy"
resultado = verify_password("1234", hash_guardado)
print("¿La contraseña coincide?:", resultado)
