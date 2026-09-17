# Job Application Pipeline

A CLI that turns a person's master data plus per-job inputs into application documents and pre-fills the employer's web form, stopping before submission so a human always sends.

## Language

**Profile**:
The applicant's master data (identity, contact details, experience, education, skills) that feeds every Application. Changes rarely.
_Avoid_: user data, CV data, resume data

**Application**:
One attempt at one job. Owns exactly one Posting, exactly one Form, its generated documents and its progress through the pipeline.
_Avoid_: job, candidacy, submission

**Posting**:
The public web page describing the job. Source of company name, role title, reference number, contact person and requirements.
_Avoid_: job description site, job ad, listing

**Form**:
The web page where the Application is actually submitted. May live on a different domain than the Posting and may sit behind a login.
_Avoid_: job application site, ATS page, portal

**Attachment**:
A static document (degree, certificate, reference letter) that is uploaded with an Application but never generated.
_Avoid_: additional document, extra file

**Source Document**:
An applicant's existing document (current CV, an old cover letter) that is read once to fill the Profile and the fixed part of the Cover Letter, and is never uploaded with an Application.
_Avoid_: old CV, input document, upload

**Template**:
An HTML/CSS document with placeholders that is rendered with Profile and Application data into a PDF.

**Cover Letter**:
The Application-specific letter, composed of a fixed part (same for every Application in a given language) and a specific part written by the applicant for this Posting.
_Avoid_: motivation letter, letter

**Language**:
The natural language an Application is written in (e.g. `de`, `en`). Profile free-text fields and Templates exist per Language; the set of Languages is open.

**Field Map**:
The per-Application record of which Form fields were detected on a Form page and which Profile value, document or Attachment each one receives. Reviewed by the applicant before filling.
_Avoid_: mapping, form config

**Synonym Table**:
The applicant-editable list of Form labels (per Language) that identify a given Profile field, e.g. "Vorname" and "First name" both mean the first name.
_Avoid_: heuristics, label dictionary

**Snapshot**:
The saved copy of a Posting (raw page plus readable text) taken when the Application was fetched, so the Posting remains available after the job is taken offline.

**Workspace**:
The directory holding one applicant's private data — Profile, Attachments, Applications, browser state and Template overrides — kept separate from the tool's own code.
_Avoid_: data folder, user folder
