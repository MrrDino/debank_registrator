import starkwareCrypto from "@starkware-industries/starkware-crypto-utils";

export default function getL2Keys(signature) {
  const priv = starkwareCrypto.keyDerivation.getPrivateKeyFromEthSignature(
    signature,
  );

  const keypair = starkwareCrypto.ec.keyFromPrivate(priv, "hex");

  const pub = keypair.getPublic(true, "hex");

  return { priv, pub };
}
