# vocabulary_formats

PCRE that verify the correctness of codes used in various medical terminologies

## Why?

In dealing with various medical terminologies, there are occassios when we need to ensure we are using valid codes from sources such as claims data, vocabulary files, or user-entered data.  It is not always feesible to compare these codes to a database of known valid codes.  The database may not be up-to-date.  There might be codes that are unknown to the database.  Access to the database might be difficult to set up.

Sometimes it's easier to see if a code "looks" like a valid code, hence these regexps.  The goal is to provide a set of regexps that verify if a code from a given terminology "looks" like the kind of code we expect.

## Skewed Towards Valid

If a choice has to be made between a more restrictive or a more permissive regexp, we'll favor the more permissive.  The point of these regexps is to see if a code _could_ be possibly valid.  If the goal is to ensure that only known, valid codes are permitted, these are not the regular expressions to use.

If the regexps are too restrictive, they might disqualify future valid codes.  For example, ICD10CM recently introduced codes that start with U, particularly for the diagnosis of COVID-related symptoms.  There are regexps in the wild that would mark these new codes as invalid.  That kind of regexp is overly restrictive for our purposes.

Basically, if the regexp yields a false negative, it's not an acceptable regexp.  If it yields a small number of false positives, we'll allow it.

## CSV Format

This respository contains a CSV file of regexps that have been gathered from various sources.  Here are the columns:

- vocabulary_id
  - Preferably the OMOP-related vocabulary_id associated with the terminology
  - e.g. ICD9CM, NDC, CPT4
- variant
  - If the regexp is meant to apply to a specific variation of the expected code format
  - e.g. ICD9CM and ICD10CM codes are often reported in Medicare claims data without the "." (dot) in the code
- regexp
  - The PCRE that matches the codes in the terminologies.  
- source
  - URL to where regexp was found, if applicable
- notes
  - Information relevant to the regexp, such as limitations, reason for the variant, etc

## Contributing

Contributions are welcome!
