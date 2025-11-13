# Solana CLI Commands Guide

This file provides an overview of common Solana CLI commands, their usage, and what they do. The Solana CLI (`solana`) is a powerful tool for interacting with the Solana blockchain, including key management, transactions, configuration, and more.

## Prerequisites
- Solana CLI installed (v1.18.26 or later).
- A Solana keypair (wallet) generated or imported.
- Configured RPC endpoint (default: devnet).

Run `solana --help` for full options.

## Configuration Commands
- **`solana config get`**: Displays the current configuration, including RPC URL, keypair path, and commitment level.
  - Example: `solana config get`
  - Output: Shows config details.

- **`solana config set --url <RPC_URL>`**: Sets the RPC endpoint (e.g., mainnet, testnet, devnet).
  - Example: `solana config set --url https://api.mainnet-beta.solana.com`
  - Use: Switch networks.

- **`solana config set --keypair <PATH>`**: Sets the default keypair file path.
  - Example: `solana config set --keypair ~/my-keypair.json`

## Keypair (Wallet) Management
- **`solana-keygen new`**: Generates a new keypair (wallet) and outputs the public key and seed phrase.
  - Example: `solana-keygen new --outfile ~/my-wallet.json`
  - Use: Create a new wallet. Back up the seed phrase securely!

- **`solana-keygen pubkey <KEYPAIR_FILE>`**: Derives the public key from a keypair file.
  - Example: `solana-keygen pubkey ~/my-wallet.json`
  - Output: Public key (address).

- **`solana-keygen recover`**: Recovers a keypair from a seed phrase.
  - Example: `solana-keygen recover 'prompt://?key=0/0'`

## Account and Balance
- **`solana balance <PUBKEY>`**: Checks the SOL balance of an account.
  - Example: `solana balance`
  - Use: View your wallet balance (defaults to configured keypair).

- **`solana airdrop <AMOUNT> <PUBKEY>`**: Requests test SOL from the faucet (devnet/testnet only).
  - Example: `solana airdrop 2` (requests 2 SOL to default account).
  - Note: Limited availability; rate-limited.

## Transactions
- **`solana transfer <RECIPIENT> <AMOUNT>`**: Transfers SOL to another account.
  - Example: `solana transfer <RECIPIENT_PUBKEY> 0.5`
  - Flags: `--fee-payer <KEYPAIR>` for custom payer.

- **`solana confirm <SIGNATURE>`**: Confirms a transaction by signature.
  - Example: `solana confirm <TX_SIGNATURE>`

## Program and Deployment
- **`solana program deploy <PROGRAM_SO>`**: Deploys a Solana program (smart contract) to the blockchain.
  - Example: `solana program deploy target/deploy/my_program.so`
  - Use: For on-chain programs (requires build with Anchor or native Rust).

- **`solana program show <PROGRAM_ID>`**: Shows details of a deployed program.
  - Example: `solana program show <PROGRAM_PUBKEY>`

## Validator and Node
- **`solana-validator`**: Starts a Solana validator node.
  - Example: `solana-validator --ledger /path/to/ledger`
  - Use: For running full nodes (resource-intensive).

- **`solana gossip`**: Shows cluster gossip information.
  - Example: `solana gossip`

## SPL Tokens (Tokens Standard)
- **`spl-token create-token`**: Creates a new token mint.
  - Example: `spl-token create-token`

- **`spl-token create-account <MINT>`**: Creates an associated token account.
  - Example: `spl-token create-account <TOKEN_MINT>`

- **`spl-token transfer <MINT> <AMOUNT> <RECIPIENT>`**: Transfers tokens.
  - Example: `spl-token transfer <MINT> 100 <RECIPIENT_ACCOUNT>`

## Utilities
- **`solana --version`**: Displays the Solana CLI version.
  - Example: `solana --version`

- **`solana help`**: Shows help for all commands.
  - Example: `solana help transfer`

- **`solana cluster-version`**: Checks the current cluster version.

## Tips
- Always use `--dry-run` for testing transactions without broadcasting.
- For mainnet, ensure you have real SOL for fees.
- Use `solana logs` to tail program logs.
- Official Docs: [Solana CLI Reference](https://docs.solana.com/cli)

For advanced usage, refer to the Solana documentation or run `solana <COMMAND> --help`.