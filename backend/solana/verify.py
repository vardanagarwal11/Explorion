import logging
import os
from solana.rpc.async_api import AsyncClient
from solders.pubkey import Pubkey
from solders.signature import Signature

logger = logging.getLogger(__name__)

TREASURY_ADDRESS = os.getenv("NEXT_PUBLIC_TREASURY_ADDRESS", "")
SOLANA_RPC_URL = os.getenv("SOLANA_RPC_URL", "https://api.devnet.solana.com")
PAPER_PRICE_SOL = 0.1

async def verify_solana_payment(signature_str: str, expected_sol: float = PAPER_PRICE_SOL) -> bool:
    """
    Verify a Solana payment transaction.
    Checks if the transaction:
    1. Exists
    2. Was successful
    3. Sent the correct amount to the treasury address
    """
    if not signature_str:
        return False
        
    if not TREASURY_ADDRESS:
        logger.warning("TREASURY_ADDRESS not configured, skipping verification (unsafe!)")
        return True

    try:
        async with AsyncClient(SOLANA_RPC_URL) as client:
            sig = Signature.from_string(signature_str)
            
            # Fetch transaction
            response = await client.get_transaction(sig, max_supported_transaction_version=0)
            if not response or not response.value:
                logger.error(f"Transaction {signature_str} not found")
                return False
                
            tx_data = response.value.transaction
            meta = response.value.transaction.meta
            
            if meta.err:
                logger.error(f"Transaction {signature_str} failed with error: {meta.err}")
                return False
                
            # Verify recipient and amount
            # Note: This is a simplified check for MVP. 
            # In production, we should iterate over instructions and check transfer amounts.
            treasury_pubkey = Pubkey.from_string(TREASURY_ADDRESS)
            
            # Simple check: did the treasury balance increase by the expected amount?
            # Find the treasury in account keys
            account_keys = tx_data.transaction.message.account_keys
            treasury_index = -1
            for i, key in enumerate(account_keys):
                if str(key) == TREASURY_ADDRESS:
                    treasury_index = i
                    break
                    
            if treasury_index == -1:
                logger.error(f"Treasury address {TREASURY_ADDRESS} not involved in transaction")
                return False
                
            # Check balance change
            pre_balance = meta.pre_balances[treasury_index]
            post_balance = meta.post_balances[treasury_index]
            change_sol = (post_balance - pre_balance) / 10**9
            
            if change_sol < (expected_sol * 0.98): # 2% tolerance for fees/dust
                logger.error(f"Insufficient payment: expected {expected_sol} SOL, got {change_sol} SOL")
                return False
                
            logger.info(f"Verified payment of {change_sol} SOL from transaction {signature_str}")
            return True
            
    except Exception as e:
        logger.error(f"Solana verification error: {str(e)}")
        return False
