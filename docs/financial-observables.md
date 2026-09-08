# Financial Observables

STIX 2.1 has no financial-transaction or bank-account observable, and STONEWORK
before this revision had only `stonework:CryptoAsset` — a `DigitalArtifact` with
three datatype properties, framed around ransomware-payment tracking. This module
adds accounts, transactions, monetary amounts, currencies, institutions, and the
"follow the money" links that connect them to the rest of the CTI graph, and
re-grounds `CryptoAsset` into that structure.

Nothing here imports an external standard. ISO 4217, ISO 13616 (IBAN), ISO 9362
(BIC), ISO 17442 (LEI), ISO 20022, and the FATF typologies are cited as sources,
not dependencies.

## Accounts

```
DigitalIdentity
└─ Account                     (abstract; range of hasAccount / accountOf)
   ├─ UserAccount              authenticated-access identity — a login
   └─ FinancialAccount         a value-holding ledger position
```

`stonework:FinancialAccount` is defined **by function**: an account that can hold
a balance of, or transfer, economic value — fiat, cryptocurrency, or a
monetary-equivalent stored value such as gift-card credit or gaming currency. It
is **not** limited to accounts at a regulated financial institution; whether one
is held at an institution is the optional `stonework:heldAt` link, and the
institution's regulatory character is a property of the institution. Account kind
(checking, exchange-hosted wallet, self-custody wallet, prepaid card, merchant
stored value, correspondent, …) is a `stonework:FinancialAccountType` applied
with `stonework:categorizedBy`.

A login and the ledgers it operates are **separate individuals** linked by
`stonework:controls` (`UserAccount → FinancialAccount`). One login commonly
controls several accounts; an account number seen in isolation has no login. This
also models account takeover directly: the `FinancialAccount` stays `accountOf`
the victim while `controls` runs from a `UserAccount` whose credentials the
attacker holds.

Identifiers attach with `stonework:hasIdentifier`: `stonework:IBAN` (the
cross-jurisdiction normalized form), `stonework:BankAccountNumber` (a domestic
number, which can coexist with an IBAN on the same account), and
`stonework:CryptoAddress` (`stonework:walletAddress`). Each currency or crypto
asset the account holds or is denominated in is linked with the intentionally
multi-valued `stonework:accountCurrency`; this supports both single-asset wallets
and multi-currency exchange accounts. A crypto address's asset is therefore
traversable as `^stonework:hasIdentifier/stonework:accountCurrency`, and a
`CryptoAsset`'s `stonework:blockchainNetwork` identifies its ledger. Institution
codes that should not broaden bare `Organization` — `stonework:bic`,
`stonework:abaRoutingNumber` — sit on `stonework:FinancialInstitution`;
`stonework:lei` sits on `stonework:Organization` because a Legal Entity
Identifier applies to any counterparty, not only institutions.

## Transactions

`stonework:FinancialTransaction` is an occurrent: `rdfs:subClassOf
stonework:CyberActivity`, a direct sibling of `Campaign`, `Incident`, and
`Operation`. It is not a reified n-ary relation — a `CyberActivity` individual
already carries properties — so subclassing gives both the event semantics
(`startedAtTime`/`endedAtTime` for initiation vs. settlement, `attributedTo`,
`Sighting`, `Investigation`, `CyberActivityCluster` membership,
`correspondsToStep`) and the n-ary carrying capacity in one class.

| Property | Meaning |
|---|---|
| `originatorAccount` / `beneficiaryAccount` | source and destination (FATF Travel Rule / ISO 20022 naming) |
| `intermediaryAccount` | correspondent hops (multi-valued, unordered in this revision) |
| `hasMonetaryValue` → `MonetaryAmount` | generic transferred sum and its currency |
| `originatorMonetaryValue` / `beneficiaryMonetaryValue` | input debited from the originator and output credited to the beneficiary; both are subproperties of `hasMonetaryValue` |
| `transactionAmount` / `transactionCurrency` | flat projections only for a single-denomination transfer |
| `usesInstrument` → `PaymentInstrument` | wire, ACH, SEPA, card, cash, on-chain, money order |
| `categorizedBy` → `TransactionType` | deposit, withdrawal, transfer, payment, currency-exchange, fee |
| `fundsActivity` → `CyberActivity` | the campaign, operation, or incident this transfer finances |
| `transactionReference` | wire reference / end-to-end ID / memo / on-chain tx hash |

Divergent source records of one economic event (originating vs. beneficiary bank,
a blockchain-analytics interpretation) are handled through `hasProvenance` and
`Sighting`, not a separate record class. A dedicated `TransactionRecord` and an
ordered correspondent chain are deferred until a reconciliation workflow needs
them.

A currency exchange can state both sides without collapsing them into one
functional currency: use `originatorMonetaryValue` for the input amount and
`beneficiaryMonetaryValue` for the output amount. Both remain visible to generic
queries through `hasMonetaryValue`. Do not assert the functional
`transactionAmount` / `transactionCurrency` convenience pair when a transaction
has different input and output denominations.

## Monetary amounts and currency

`stonework:MonetaryAmount` reifies magnitude (`stonework:amount`, `xsd:decimal`)
and unit (`stonework:currency`) so the two always travel together — the same
choice `stonework:Hash` makes for algorithm and digest. `stonework:hasMonetaryValue`
attaches one to a `FinancialTransaction`, `FinancialAccount`, or `Impact`. The
baseline SHACL profile requires every `MonetaryAmount` to have exactly one
decimal `amount` and exactly one `Currency`.

`stonework:Currency` is the unit of denomination:

- **Fiat** — a closed controlled vocabulary, `stonework:fiatCurrencyScheme`
  (`dcterms:source` ISO 4217), with `skos:notation` the alpha-3 code and
  `stonework:minorUnitDigits` the decimal precision. Seed only the currencies a
  consuming graph uses.
- **Crypto** — open. Each coin or token is a `stonework:CryptoAsset` individual,
  created as needed.

A **time- and rate-sensitive valuation** — the USD equivalent of a crypto
transfer at a stated moment — is deliberately kept out of `MonetaryAmount`. It is
a `stonework:MetricObservation` (`metricType stonework:metricNormalizedValue`,
`observedAt`, `metricValue`, and `valuationCurrency`) attached to the
`MonetaryAmount` via `stonework:hasMetricObservation` — the amount is a
`CyberEntity`, and the observation carries the time the valuation applies to.
`stonework:valuationCurrency` makes the value's output unit machine-readable;
`stonework:hasProvenance` cites the concrete exchange-rate source. The strict
SHACL profile requires that provenance, while the baseline profile requires a
normalized valuation to have exactly one decimal value and one currency.

## CryptoAsset, re-grounded

`stonework:CryptoAsset` kept its IRI and changed meaning: it is now **the asset**
(Bitcoin, Ether, a specific token), `rdfs:subClassOf stonework:Currency`. Its
`skos:altLabel` is "virtual asset" (the FATF term). The same nominal token issued
on multiple ledgers is distinct individuals, distinguished by
`stonework:blockchainNetwork` (kept a free string). A wallet is now a
`stonework:FinancialAccount`; its address is a `stonework:CryptoAddress`, onto
which `stonework:walletAddress` was re-domained. The wallet's
`stonework:accountCurrency` points to the asset, making the full
address-to-network path explicit rather than inferring it from address syntax.

**Breaking change:** `stonework:cryptoCurrency` (the `"BTC"` string property) is
**removed**. Replace it by linking the amount or wallet to the `CryptoAsset`
individual.

## Illicit-finance techniques

The core defines two neutral structural slots and no individuals:

- `stonework:IllicitFinanceTechnique rdfs:subClassOf stonework:Technique` —
  covers money-laundering typologies and the adjacent methods of terrorist
  financing, sanctions evasion, and fraud.
- `stonework:LaunderingStage rdfs:subClassOf stonework:Tactic` — placement,
  layering, integration.

`ontologies/frameworks/fatf.ttl` populates them with ten FATF-derived typology
individuals and the three stages (each `stonework:hasTechnique` its typologies),
every one carrying `dcterms:source`. The module states plainly that it is
illustrative, non-exhaustive, and non-normative; other bodies' typology sets can
populate the same slots. This mirrors `frameworks/killchain.ttl` — abstract class
in core, curated individuals in a framework module.

For v1 a transaction or a `CyberActivityCluster` links to a typology with the
open-domain `stonework:hasBehavior`. Because the class sits under `Technique`, a
later revision can model a concrete laundering chain as a `stonework:Procedure`
that `stonework:implements` a typology, decomposed into `stonework:Step`s, with
no rework.

## Worked example

`examples/financial-follow-the-money.ttl` traces the proceeds of a ransomware
incident: a Bitcoin ransom payment to the actor's collection wallet, then
mixing, a chain-hop with explicit BTC input and XMR output amounts, a deposit to
a hosted account at a non-compliant exchange operated through a money mule's KYC
login, and a wire cash-out into the mule's bank account. The ransom amount also
has a USD-normalized observation with an explicit valuation currency and cited
rate source. The five transfers are one `stonework:CyberActivityCluster`
attributed to the actor, exhibiting `fatf:Layering`, `fatf:CryptoMixing`,
`fatf:ChainHopping`, and `fatf:MoneyMuleNetwork`, and linked to the incident with
`stonework:fundsActivity`.

The money is traversable in one query — from the incident, along
`beneficiaryAccount` / `^originatorAccount` alternately, to the mule's IBAN and
the people on the path:

```sparql
PREFIX stonework: <https://cyberterrain.org/ns/stonework#>
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
PREFIX ex: <https://cyberterrain.org/ns/stonework/examples/follow-the-money#>

SELECT ?hop ?type ?from ?to ?toIban ?exhibits WHERE {
  ?first stonework:fundsActivity ex:incident-ransom .
  ?first (stonework:beneficiaryAccount/^stonework:originatorAccount)* ?hop .
  ?hop stonework:originatorAccount ?fromAcct ;
       stonework:beneficiaryAccount ?toAcct ;
       stonework:startedAtTime ?t .
  OPTIONAL { ?hop stonework:categorizedBy ?tt . ?tt skos:notation ?type }
  OPTIONAL { ?fromAcct stonework:accountOf ?a1 . ?a1 skos:prefLabel ?from }
  OPTIONAL { ?toAcct   stonework:accountOf ?a2 . ?a2 skos:prefLabel ?to }
  OPTIONAL { ?toAcct   stonework:hasIdentifier ?id . ?id stonework:iban ?toIban }
  OPTIONAL { ?hop stonework:hasBehavior ?b .
             ?b a stonework:IllicitFinanceTechnique ; skos:prefLabel ?exhibits }
}
ORDER BY ?t
```

Result (RDF4J in-memory, loading `stonework.ttl`, `categories.ttl`,
`frameworks/fatf.ttl`, and the example):

| hop | type | from | to | toIban | exhibits |
|---|---|---|---|---|---|
| `ex:txn-ransom-payment` | payment | Example victim company | Example ransomware crew | | |
| `ex:txn-mix` | transfer | Example ransomware crew | Example ransomware crew | | Crypto Mixing |
| `ex:txn-chain-hop` | currency-exchange | Example ransomware crew | Example ransomware crew | | Chain Hopping |
| `ex:txn-exchange-deposit` | deposit | Example ransomware crew | Example ransomware crew | | |
| `ex:txn-cashout` | withdrawal | Example ransomware crew | Example money mule | GB29EXMP60161331926819 | Money Mule Network |

## Deferred

`TransactionRecord` (multi-source reconciliation), an ordered correspondent
chain, a `FinancialActivity` grouping class, stablecoin and CBDC modeling, an
`illicitFinancePurposeScheme`, laundering `Procedure`/`Step` depth, a
`blockchainNetworkScheme`, and a `QuantityValue` grouping over `MonetaryAmount`.
