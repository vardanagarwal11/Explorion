/**
 * Solana helpers for Explorion frontend.
 *
 * Handles transaction building, payment verification,
 * and balance formatting for the royalty settlement layer.
 */

import {
  Connection,
  PublicKey,
  SystemProgram,
  Transaction,
  LAMPORTS_PER_SOL,
} from "@solana/web3.js";

// ═══════════════════════════════════════════════════════════
// Constants
// ═══════════════════════════════════════════════════════════

/** Default paper price: 0.1 SOL */
export const PAPER_PRICE_SOL = 0.1;
export const PAPER_PRICE_LAMPORTS = PAPER_PRICE_SOL * LAMPORTS_PER_SOL;

/** Revenue split */
export const PLATFORM_SHARE_BPS = 8000; // 80%
export const RESEARCHER_SHARE_BPS = 2000; // 20%

/** Solana network */
export const SOLANA_NETWORK =
  (process.env.NEXT_PUBLIC_SOLANA_NETWORK as "devnet" | "mainnet-beta") ||
  "devnet";

export const SOLANA_RPC_URL =
  process.env.NEXT_PUBLIC_SOLANA_RPC_URL ||
  (SOLANA_NETWORK === "devnet"
    ? "https://api.devnet.solana.com"
    : "https://api.mainnet-beta.solana.com");

/** Platform treasury address */
export const TREASURY_ADDRESS =
  process.env.NEXT_PUBLIC_TREASURY_ADDRESS || "";

// ═══════════════════════════════════════════════════════════
// Helpers
// ═══════════════════════════════════════════════════════════

/**
 * Format lamports as SOL string with specified decimal places.
 */
export function formatSol(lamports: number, decimals = 4): string {
  return (lamports / LAMPORTS_PER_SOL).toFixed(decimals);
}

/**
 * Format lamports as a display-friendly SOL string.
 */
export function formatSolDisplay(lamports: number): string {
  const sol = lamports / LAMPORTS_PER_SOL;
  if (sol >= 1000) return `${(sol / 1000).toFixed(1)}K SOL`;
  if (sol >= 1) return `${sol.toFixed(2)} SOL`;
  return `${sol.toFixed(4)} SOL`;
}

/**
 * Calculate the revenue split for a given amount.
 */
export function calculateSplit(amountLamports: number) {
  const researcherShare = Math.floor(
    (amountLamports * RESEARCHER_SHARE_BPS) / 10000
  );
  const platformShare = amountLamports - researcherShare;
  return { researcherShare, platformShare };
}

/**
 * Truncate a Solana address for display.
 */
export function truncateAddress(address: string, chars = 4): string {
  return `${address.slice(0, chars)}...${address.slice(-chars)}`;
}

// ═══════════════════════════════════════════════════════════
// Transaction Building
// ═══════════════════════════════════════════════════════════

/**
 * Build a payment transaction for paper exploration.
 *
 * Creates a transaction that splits payment between:
 * - Platform treasury (80%)
 * - Researcher escrow vault (20%) — held in vault PDA
 *
 * For MVP, this sends a simple SOL transfer to the treasury.
 * The on-chain program handles the split once deployed.
 */
export async function buildPaymentTransaction(
  connection: Connection,
  payerPubkey: PublicKey,
  amountLamports: number = PAPER_PRICE_LAMPORTS,
): Promise<Transaction> {
  if (!TREASURY_ADDRESS) {
    throw new Error("Treasury address not configured");
  }

  const treasuryPubkey = new PublicKey(TREASURY_ADDRESS);
  const { researcherShare, platformShare } = calculateSplit(amountLamports);

  const transaction = new Transaction();

  // For MVP: send full amount to treasury
  // After Anchor program deployment, this will call pay_for_paper() instead
  transaction.add(
    SystemProgram.transfer({
      fromPubkey: payerPubkey,
      toPubkey: treasuryPubkey,
      lamports: amountLamports,
    })
  );

  const { blockhash } = await connection.getLatestBlockhash();
  transaction.recentBlockhash = blockhash;
  transaction.feePayer = payerPubkey;

  return transaction;
}

// ═══════════════════════════════════════════════════════════
// API Integration
// ═══════════════════════════════════════════════════════════

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

/**
 * Verify a payment with the backend.
 */
export async function verifyPayment(params: {
  txSignature: string;
  contentId: string;
  paperHash: string;
  learnerWallet: string;
  amountLamports: number;
}) {
  const res = await fetch(`${API_BASE}/api/payment/verify`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      tx_signature: params.txSignature,
      content_id: params.contentId,
      paper_hash: params.paperHash,
      learner_wallet: params.learnerWallet,
      amount_lamports: params.amountLamports,
    }),
  });

  if (!res.ok) {
    const err = await res.text();
    throw new Error(`Payment verification failed: ${err}`);
  }

  return res.json();
}

/**
 * Get royalty status for a paper.
 */
export async function getRoyaltyStatus(paperHash: string) {
  const res = await fetch(
    `${API_BASE}/api/payment/status/${encodeURIComponent(paperHash)}`
  );
  if (res.status === 404) return null;
  if (!res.ok) throw new Error(`Failed to get royalty status: ${res.status}`);
  return res.json();
}

/**
 * Get researcher dashboard data.
 */
export async function getResearcherDashboard(walletAddress: string) {
  const res = await fetch(
    `${API_BASE}/api/researcher/dashboard?wallet=${encodeURIComponent(
      walletAddress
    )}`
  );
  if (!res.ok)
    throw new Error(`Failed to get researcher dashboard: ${res.status}`);
  return res.json();
}
