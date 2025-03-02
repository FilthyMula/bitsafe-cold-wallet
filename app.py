from flask import Flask, g, render_template, request, send_file, jsonify
from bip32utils import BIP32Key
from mnemonic import Mnemonic
from bit import wif_to_key
import qrcode
import os

app = Flask(__name__)

DATA_FOLDER = "wallet_data"
SEED_FILE = os.path.join(DATA_FOLDER, "seed.txt")
PUBLIC_KEY_FILE = os.path.join(DATA_FOLDER, "public_key.txt")

os.makedirs(DATA_FOLDER, exist_ok=True)

def generate_seed_phrase():
    return Mnemonic("english").generate(strength=256)

def seed_to_private_key(seed_phrase):
    seed_bytes = Mnemonic("english").to_seed(seed_phrase)
    master_key = BIP32Key.fromEntropy(seed_bytes)
    child_key = master_key.ChildKey(0).ChildKey(0)

    private_key_wif = child_key.WalletImportFormat()
    public_address = child_key.Address()

    return private_key_wif, public_address

def create_wallet():
    seed_phrase = generate_seed_phrase()
    private_key_wif, public_address = seed_to_private_key(seed_phrase)

    with open(SEED_FILE, "w") as f:
        f.write(seed_phrase)
    with open(PUBLIC_KEY_FILE, "w") as f:
        f.write(public_address)

    return public_address

def load_wallet():
    if os.path.exists(SEED_FILE):
        with open(SEED_FILE, "r") as f:
            seed_phrase = f.read().strip()

        private_key_wif, public_address = seed_to_private_key(seed_phrase)

        return private_key_wif, public_address
    else:
        return None, create_wallet()

@app.before_request
def load_wallet_data():
    _, g.wallet_address = load_wallet()

@app.route("/")
def wallet():
    return render_template("wallet.html", address=g.wallet_address)

@app.route("/qrcode/<btc_address>")
def generate_qr(btc_address):
    img = qrcode.make(btc_address)
    img_path = os.path.join("static", "qrcodes", f"{btc_address}.png")
    os.makedirs(os.path.dirname(img_path), exist_ok=True)
    img.save(img_path)
    return send_file(img_path, mimetype="image/png")

@app.route("/sign_transaction", methods=["POST"])
def sign_transaction():
    data = request.json
    to_address = data.get("to_address")
    amount = data.get("amount")

    if not to_address or not amount:
        return jsonify({"error": "Invalid input"}), 400

    private_key_wif, _ = load_wallet()

    if private_key_wif is None:
        return jsonify({"error": "Wallet not found"}), 404

    key = wif_to_key(private_key_wif)
    tx = key.create_transaction([(to_address, amount, "btc")])

    return jsonify({"signed_tx": tx})

if __name__ == "__main__":
    app.run(debug=True)