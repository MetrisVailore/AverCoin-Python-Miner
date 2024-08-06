from AverWalletTools import AverWallet

wallet = AverWallet().Wallet.create_wallet()
address = wallet["address"]
print(f"Публичный ключ {address['pbc']}")
print(f"Приватный ключ {address['pve']}")