# Golden Set Labelling Protocol

## 1. Purpose

This document defines the rules and workflow for creating the team's
human-labelled golden test set.

The purpose of this protocol is to ensure that all annotators apply the
same classification rules, work independently, and produce labels that
can be used to calculate inter-annotator agreement and create a frozen
golden set for later model benchmarking.

This protocol applies to the following seven categories:

1.  Credit reporting
2.  Debt collection
3.  Mortgage
4.  Credit card
5.  Bank account or service
6.  Consumer loan
7.  Money transfer or service

The source CSV's existing `source_label` must **not** be treated as
ground truth when assigning human labels.

------------------------------------------------------------------------

## 2. Protocol Status

**Protocol version:** 1.1\
**Status:** Complete working protocol\
**Approval:** The team should review this document before annotation
begins.

The rules below are the operational rules to be used by both annotators.
If the team changes a rule before annotation, the change must be
recorded in the revision history and both annotators must use the same
updated version.

Once annotation begins, annotators must not independently change the
rules.

------------------------------------------------------------------------

# 3. Category Definitions

## 3.1 Credit reporting

### Definition

A complaint primarily about a consumer report, credit file, credit
score, or the preparation, accuracy, access, or use of credit-reporting
information.

### Include

-   Incorrect, incomplete, outdated, mixed, or unauthorized information
    in a credit report.
-   Problems obtaining a credit report.
-   Problems correcting or disputing information on a credit report.
-   Incorrect account information reported to a credit bureau.
-   Unauthorized or incorrect credit inquiries.
-   Identity mix-ups affecting a credit file.
-   A complaint where the credit report or score is itself the main
    subject of the complaint.

### Exclude

-   A complaint about the underlying loan, credit card, or collection
    activity where credit reporting is only mentioned as a consequence.
-   A complaint where the main problem is collection conduct rather than
    the reporting of the debt.

### Common indicators

-   Credit report
-   Credit file
-   Credit bureau
-   Credit score
-   Tradeline
-   Credit inquiry
-   Hard inquiry
-   Dispute
-   Reinvestigation
-   Inaccurate information
-   Identity mix-up

### Edge cases

If both collection conduct and credit reporting are mentioned, classify
according to the dominant complaint. If the consumer is primarily asking
for incorrect reporting to be corrected, use **Credit reporting**. If
the consumer is primarily complaining about collection activity, use
**Debt collection**.

------------------------------------------------------------------------

## 3.2 Debt collection

### Definition

A complaint primarily about attempts to collect a debt or the conduct of
a debt collector, collection agency, or other party engaged in debt
collection.

### Include

-   Repeated or improper collection contact.
-   Threats or harassment by a collector.
-   Collection of a debt the consumer disputes or says they do not owe.
-   Failure to validate a debt.
-   Collection after payment or settlement.
-   Collection-related fees.
-   Collection activity that includes related credit reporting when
    collection conduct is the main complaint.

### Exclude

-   A complaint about an original lender's normal account servicing when
    no collection activity is involved.
-   Complaints primarily about loan terms or account servicing.
-   Complaints primarily about incorrect credit reporting when
    collection conduct is only background information.

### Common indicators

-   Debt collector
-   Collection agency
-   Collection calls
-   Collection letters
-   Validation
-   Disputed debt
-   Settlement
-   Garnishment
-   Debt collection

### Edge cases

If an original creditor is collecting its own overdue debt, use **Debt
collection** when the complaint is specifically about collection
conduct. If the complaint is instead about the underlying loan or
account servicing, use the relevant product category.

------------------------------------------------------------------------

## 3.3 Mortgage

### Definition

A complaint primarily about a home mortgage loan, mortgage servicing,
mortgage origination, or foreclosure process.

### Include

-   Mortgage payments.
-   Escrow.
-   Mortgage statements.
-   Mortgage fees.
-   Loan modification.
-   Mortgage refinancing.
-   Foreclosure.
-   Mortgage payoff.
-   Mortgage servicing.
-   Transfer of mortgage servicing.

### Exclude

-   Non-mortgage consumer loans.
-   Credit cards.
-   Deposit accounts.
-   Debt collection when collection conduct is the primary complaint.

### Common indicators

-   Mortgage
-   Home loan
-   Mortgage servicer
-   Escrow
-   Foreclosure
-   Loan modification
-   Refinancing
-   Mortgage payment
-   Mortgage payoff

### Edge cases

If foreclosure and credit reporting are both mentioned, classify
according to the dominant complaint. If the main requested remedy
concerns the mortgage or foreclosure, use **Mortgage**. If the main
requested remedy concerns inaccurate credit reporting, use **Credit
reporting**.

------------------------------------------------------------------------

## 3.4 Credit card

### Definition

A complaint primarily about a credit card account, credit card issuer,
credit-card billing, or credit-card borrowing.

### Include

-   Unauthorized or incorrect credit-card charges.
-   Billing disputes.
-   Credit-card fees.
-   Credit-card interest.
-   Payment allocation.
-   Credit-card account opening or closure.
-   Credit limits.
-   Credit-card issuer service.
-   Credit-card statements.
-   Incorrect balances.

### Exclude

-   Debit-card transactions tied to a deposit account; use **Bank
    account or service**.
-   Prepaid, gift, and other stored-value cards with no credit line; use
    **Bank account or service** (see section 3.5 edge cases).
-   Standalone money-transfer or wallet problems where the transfer
    provider's handling is the main issue.
-   Personal, auto, payday, or other consumer loans.

### Common indicators

-   Credit card
-   Card issuer
-   Statement balance
-   APR
-   Minimum payment
-   Card fee
-   Disputed purchase
-   Credit limit

### Edge cases

If a credit card is used to fund a transfer, classify according to the
service actually being disputed. If the complaint is about the card
issuer's handling of the card transaction, use **Credit card**. If the
complaint is about the transfer provider's handling of the money
transfer, use **Money transfer or service**.

------------------------------------------------------------------------

## 3.5 Bank account or service

### Definition

A complaint primarily about a deposit account or a banking service
associated with that account.

### Include

-   Checking accounts.
-   Savings accounts.
-   Deposits.
-   Withdrawals.
-   Overdrafts.
-   Account access.
-   Account closure.
-   Bank account fees.
-   Debit-card transactions associated with a bank account.
-   Prepaid, gift, and other stored-value cards (forced closest fit; see
    edge cases below).

### Exclude

-   Credit-card borrowing.
-   Consumer-loan servicing.
-   Mortgage servicing.
-   Standalone transfer or remittance services when the transfer service
    is the main issue.

### Common indicators

-   Checking
-   Savings
-   Deposit
-   Withdrawal
-   Overdraft
-   Debit card
-   Frozen account
-   Closed account
-   Bank account fee

### Edge cases

For a debit-card purchase dispute, use **Bank account or service** when
the debit card/deposit account is the subject of the complaint.

For money sent through a separate transfer service, use **Money transfer
or service** when the transfer provider's handling is the main
complaint.

Prepaid, gift, and other stored-value cards (for example a loaded
network-branded gift card or a prepaid benefits debit card) are funds-loaded
payment cards with no credit line. Classify them as **Bank account or
service** and record in `notes` that this is a forced closest fit. Use
**Credit card** only if the card carries a credit line, and **Money transfer
or service** only if the complaint is about a transfer provider moving money
between parties.

------------------------------------------------------------------------

## 3.6 Consumer loan

### Definition

A complaint primarily about a non-mortgage consumer loan, vehicle
financing/lease, or the lender's terms or servicing.

### Include

-   Personal loans.
-   Auto or vehicle loans.
-   Payday loans.
-   Title loans.
-   Instalment loans.
-   Vehicle financing.
-   Vehicle leases.
-   Loan applications.
-   Loan payments.
-   Loan fees.
-   Loan interest.
-   Loan servicing.
-   Repossession.

### Exclude

-   Home mortgages.
-   Credit-card accounts.
-   Deposit accounts.
-   Debt collection conduct when collection activity is the primary
    complaint.
-   Money-transfer services.

### Common indicators

-   Personal loan
-   Auto loan
-   Vehicle financing
-   Payday loan
-   Title loan
-   Instalment payment
-   Lender
-   Repossession
-   Lease

### Edge cases

Student loans and other products that do not clearly fit the listed
examples must be classified according to the closest defensible category
only if the narrative provides sufficient evidence. If no defensible
category exists, mark the case for human adjudication before the golden
set is frozen.

------------------------------------------------------------------------

## 3.7 Money transfer or service

### Definition

A complaint primarily about sending, receiving, or moving money through
a transfer provider, remittance service, payment wallet, or similar
money-transfer service.

### Include

-   Wire transfers.
-   Remittances.
-   Money orders.
-   Person-to-person transfers.
-   Digital wallets.
-   Virtual-currency transfers.
-   Money that is missing, delayed, misdirected, blocked, or incorrectly
    handled by a transfer service.

### Exclude

-   Ordinary card purchases where the card issuer is the principal
    subject.
-   Deposit-account transactions where the bank account service is the
    principal subject.
-   Loan or mortgage servicing.
-   Debt collection.

### Common indicators

-   Wire
-   Remittance
-   Money order
-   Transfer
-   Wallet
-   Payment app
-   Funds sent
-   Funds received
-   Virtual currency

### Edge cases

If a wallet or transfer service is linked to a bank or credit card,
classify according to the provider/service whose handling is actually
being complained about, rather than simply the source of the funds.

------------------------------------------------------------------------

# 4. General Labelling Rules

## 4.1 One category per ticket

Every selected ticket receives exactly **one** category from the seven
permitted categories.

Do not assign multiple categories.

The annotator must identify the category that best represents the
primary complaint.

------------------------------------------------------------------------

## 4.2 Multiple matching categories

When a narrative appears to match multiple categories:

1.  Identify the main harm described by the consumer.
2.  Identify the remedy or correction the consumer is primarily seeking.
3.  Identify the product or service most directly responsible for that
    harm.
4.  Select the single category that best satisfies those three
    considerations.
5.  Record a short explanation in `notes` when the case is genuinely
    ambiguous.

The presence of a secondary product or issue does not automatically
change the category.

### Tie-break rule

If two categories remain equally plausible:

-   Prefer the issue associated with the consumer's main requested
    remedy.
-   If the requested remedy does not resolve the tie, prefer the
    product/service most directly responsible for the disputed action.
-   If the case still cannot be distinguished, select the best-supported
    category and record the ambiguity in `notes`.
-   The case must be reviewed during disagreement resolution if the
    annotators select different categories.

------------------------------------------------------------------------

## 4.3 Ambiguous narratives

Use only information explicitly supported by the narrative.

Do **not** invent missing facts.

When a narrative is ambiguous:

1.  Identify all categories supported by the text.
2.  Apply the multiple-category and dominant-complaint rules.
3.  Select the best-supported category.
4.  Record the ambiguity briefly in `notes`.

Do not create a new category.

------------------------------------------------------------------------

## 4.4 Tickets that appear to fit none

The final schema contains only seven categories.

If the narrative does not clearly fit any category:

1.  Do not invent facts.
2.  Do not create a new category.
3.  If there is a defensible closest category, use it and record that it
    is a forced closest fit in `notes`.
4.  If no category can reasonably be defended, record the issue in
    `notes` and escalate the ticket for human team adjudication before
    the golden set is frozen.

A ticket must not silently receive an arbitrary label merely to complete
the sheet.

------------------------------------------------------------------------

## 4.5 Dominant complaint

The dominant complaint is the issue that best explains:

-   Why the consumer contacted the company.
-   What harm the consumer is primarily describing.
-   What correction or remedy the consumer chiefly wants.

Background information and downstream consequences should normally not
determine the category unless the consumer makes them the principal
complaint.

------------------------------------------------------------------------

## 4.6 Insufficient or unintelligible narratives

Do not guess from a product name alone.

If the narrative is incomplete, unintelligible, or lacks enough
information to classify confidently:

-   Select a category only if a defensible classification is possible.
-   Record the limitation in `notes`.
-   Escalate cases with no defensible classification for human review
    before freezing the golden set.

------------------------------------------------------------------------

## 4.7 Duplicate narratives

Duplicate narratives are not automatically removed.

Each selected source row remains a separate observation and must be
labelled according to its own row.

Do not delete duplicate rows from the golden-set sample unless the
agreed dataset-selection procedure explicitly identifies them as
duplicates to be excluded before annotation.

------------------------------------------------------------------------

# 5. Independent Annotation Procedure

## 5.1 Preparation

Before annotation:

1.  The team approves this protocol.
2.  The golden-set sample is selected deterministically.
3.  The original source row numbers are preserved.
4.  Annotator A and Annotator B receive identical ticket selections.
5.  Each annotator receives the same approved protocol version.
6.  Each annotator receives only their own labelling sheet.

------------------------------------------------------------------------

## 5.2 Annotator A

Annotator A must:

1.  Read the approved protocol.
2.  Review each selected ticket independently.
3.  Assign exactly one of the seven permitted categories.
4.  Add optional notes where useful.
5.  Save the completed annotation sheet.
6.  Submit it without viewing Annotator B's labels.

Annotator A must not copy, infer, or coordinate labels with Annotator B.

------------------------------------------------------------------------

## 5.3 Annotator B

Annotator B follows exactly the same procedure independently.

Annotator B must not view Annotator A's completed sheet before
submitting their own labels.

------------------------------------------------------------------------

## 5.4 Independence requirement

The two initial annotation sheets are evidence of independent human
judgement.

Neither annotator may change an original annotation merely to increase
agreement.

Original labels must remain unchanged after submission.

------------------------------------------------------------------------

# 6. Agreement Calculation

Agreement is calculated only after both annotators have independently
completed their sheets.

The agreement script must first verify:

-   Both files contain the same selected row numbers.
-   Narratives match.
-   Every selected ticket has a nonblank label.
-   Every label belongs to the seven permitted categories.
-   There are no duplicate row numbers.

If validation fails, agreement must not be calculated until the problem
is corrected.

## 6.1 Metrics

Report:

1.  Total tickets
2.  Number agreed
3.  Number disagreed
4.  Raw percentage agreement
5.  Unweighted Cohen's kappa

### Raw percentage agreement

``` text
Raw agreement = number agreed / total tickets
```

Report it as a percentage.

### Cohen's kappa

Cohen's kappa measures agreement between two annotators while accounting
for agreement expected by chance.

The calculation is:

``` text
kappa = (Po - Pe) / (1 - Pe)
```

where:

-   `Po` = observed agreement
-   `Pe` = expected agreement by chance

If expected agreement is exactly 1, Cohen's kappa is undefined and must
be reported as `null` rather than inventing a value.

Do not fabricate agreement statistics before both annotation sheets are
complete.

------------------------------------------------------------------------

# 7. Disagreement Resolution

A disagreement occurs whenever Annotator A and Annotator B assign
different categories to the same row.

## 7.1 Resolution process

For every disagreement:

1.  Preserve both original labels.
2.  Compare the ticket against the approved protocol.
3.  Annotators discuss the applicable rule.
4.  If they reach agreement, record the agreed final category and
    rationale.
5.  If they cannot agree, a third human team member who did not make
    either original annotation adjudicates the case.
6.  The adjudicator selects one of the seven permitted categories.
7.  Record the final category and the reasoning.

The original annotation sheets must **not** be edited to make them
agree.

------------------------------------------------------------------------

## 7.2 Disagreement report

Each disagreement must contain:

-   Original row number
-   Narrative
-   Annotator A label
-   Annotator B label
-   Final resolved label
-   Resolution notes
-   Whether the protocol was updated

The `final_resolved_label` remains blank until the human resolution is
completed.

------------------------------------------------------------------------

## 7.3 Protocol changes caused by disagreements

If a disagreement reveals that the protocol is incomplete or unclear:

1.  Identify the missing or unclear rule.
2.  Update the protocol.
3.  Record the change in the revision history.
4.  The team decides whether previously affected tickets must be
    relabelled by both annotators.
5.  Apply the new rule consistently to all affected tickets.

Do not silently apply a new rule to only one ticket.

------------------------------------------------------------------------

# 8. Final Golden Set

The final golden set is created only after:

-   Both independent annotation sheets are complete.
-   Agreement has been calculated.
-   All disagreements have been resolved by humans.
-   All required validation checks pass.
-   The final set contains between 150 and 200 tickets.

For tickets where both annotators agree, the shared label becomes the
final category.

For tickets where they disagree, the human-resolved label becomes the
final category.

The final golden set must contain:

  Column                    Description
  ------------------------- -------------------------------
  `row`                     Original source row number
  `narrative`               Original ticket narrative
  `final_golden_category`   Final human-approved category

Do not modify the original source CSV.

------------------------------------------------------------------------

# 9. Freeze Protection

The golden set must be treated as a controlled evaluation artifact.

**THE GOLDEN SET MUST BE FINALISED AND COMMITTED BEFORE MODEL
BENCHMARKING.**

Once frozen:

-   Do not automatically regenerate or overwrite it.
-   Do not change labels based on model performance.
-   Do not add or remove tickets simply because a model performs poorly
    or well.
-   Do not use model predictions to change human labels.
-   Any post-freeze change must be explicitly documented and approved by
    the team.
-   If the golden set is changed, create a new version rather than
    silently replacing the previous frozen version.

The benchmark must use the frozen golden-set version that was committed
before benchmarking began.

------------------------------------------------------------------------

# 10. Validation Checklist

Before finalizing the golden set, run checks for:

-   [ ] Duplicate row numbers
-   [ ] Missing labels
-   [ ] Invalid categories
-   [ ] Missing narratives
-   [ ] Mismatched Annotator A and B files
-   [ ] Unresolved disagreements
-   [ ] Incorrect number of golden tickets
-   [ ] Missing final resolved labels for disagreements
-   [ ] Missing resolution notes
-   [ ] Invalid `protocol_updated` values
-   [ ] Changes to original source rows
-   [ ] Final set contains 150--200 tickets

The finalizer must refuse to produce or overwrite the frozen golden set
if these checks fail.

------------------------------------------------------------------------

# 11. Human Decisions and Approval

The following decisions are fixed by this protocol unless the team
explicitly changes them before annotation:

  -----------------------------------------------------------------------
  Decision                            Operational rule
  ----------------------------------- -----------------------------------
  Number of labels                    Exactly one of seven categories per
                                      ticket

  Multiple categories                 Select the dominant complaint

  Dominant complaint                  Main harm, requested remedy, and
                                      directly responsible
                                      product/service

  Ambiguous narratives                Use only stated evidence; select
                                      best-supported category and record
                                      ambiguity

  None-of-seven                       Use closest defensible category;
                                      escalate cases with no defensible
                                      fit

  Unusable narratives                 Do not invent information; escalate
                                      if no defensible classification
                                      exists

  Duplicate narratives                Keep selected rows and label each
                                      independently

  Annotator independence              No cross-viewing or coordination
                                      before submission

  Disagreement                        Human resolution; third human
                                      adjudicator if needed

  Original labels                     Never alter after submission

  Protocol changes                    Document and apply consistently to
                                      affected tickets

  Golden-set size                     150--200 tickets

  Freeze point                        Before model benchmarking

  Post-freeze changes                 New documented version; no silent
                                      overwrite
  -----------------------------------------------------------------------

------------------------------------------------------------------------

# 12. Documentation Workflow

The team must document the following:

1.  How tickets were selected.
2.  Which original row numbers were selected.
3.  How Annotator A labelled the tickets.
4.  How Annotator B labelled the tickets.
5.  Which protocol version they used.
6.  How agreement was calculated.
7.  The resulting agreement statistics.
8.  Which tickets disagreed.
9.  How disagreements were resolved.
10. Whether the protocol was updated as a result.
11. How the final golden set was generated.
12. Which version of the golden set was frozen.
13. When the frozen golden set was committed.
14. Confirmation that freezing occurred before model benchmarking.

------------------------------------------------------------------------

# 13. Required Human Actions Before Annotation

Before either annotator begins:

-   Review this protocol together.
-   Confirm that all seven category definitions are acceptable.
-   Confirm the multiple-category and dominant-complaint rules.
-   Confirm how ambiguous and none-of-seven cases are handled.
-   Confirm the disagreement process.
-   Confirm the row-number convention used by the dataset.
-   Record any changes in the revision history.
-   Approve the final protocol version.

After approval, both annotators must use exactly the same protocol
version.

------------------------------------------------------------------------

# 14. Revision History

  -----------------------------------------------------------------------
  Version           Date              Changes           Agreed by
  ----------------- ----------------- ----------------- -----------------
  0.2-draft         2026-10-06        Initial proposed  Pending
                                      category and      
                                      adjudication      
                                      rules             

  1.0               2026-10-06        Completed         Team approval
                                      operational rules required
                                      for annotation,   
                                      ambiguity,        
                                      multiple          
                                      categories,       
                                      disagreement      
                                      resolution,       
                                      validation, and   
                                      golden-set        
                                      freezing          

  1.1               2026-10-06        Added rule for     Team approval
                                      prepaid, gift and  
                                      stored-value       
                                      cards (sections    
                                      3.4, 3.5), from    
                                      disagreement rows
                                      7382 and 7882.
                                      Affected agreed
                                      tickets 7521 and
                                      7657 already
                                      labelled Bank
                                      account or
                                      service.
  -----------------------------------------------------------------------
