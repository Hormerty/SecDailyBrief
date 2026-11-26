SecDailyBrief 1.7.3
===================

A daily cyber-security brief by e-mail, composed from public sources and adapted to your
stack. No account, no telemetry.

This program does not monitor your computer. It reads none of your documents, captures
nothing and transmits nothing to its author. It downloads information from public feeds,
summarises it, then sends the result to the address you chose, through your own mail server.
Your settings stay on this machine and are erased with one click.

The program does not run continuously: it wakes up, works for one to two minutes, then
stops.


GETTING STARTED
---------------

1. Double-click SecDailyBrief.exe.
   Windows may show "Windows protected your PC": the program is not code-signed. Click
   "More info", then "Run anyway".

2. The wizard asks for the language, then your sending address.

3. For Gmail, you need an app password, not your usual password:
   https://myaccount.google.com/apppasswords
   That page only exists if two-step verification is enabled on your account.

4. The "Test sending" button checks the configuration before saving it.

5. At the end, a scheduled task is created for the time you chose (06:00 by default).


WHERE MY DATA LIVES
-------------------

In %APPDATA%\SecDailyBrief:

   config.json       your settings (addresses, time, time zone)
   perimetre.json    the countries and products you watch
   secret.dpapi      the password, encrypted by Windows (unreadable on another machine)
   journal.log       the log of every run
   historique.json   the latest runs, summarised (seven days on screen)
   seen.json, stats.db, ...   the engine's state

None of these files holds a password in clear text. The "Delete all my data" button in the
panel erases the whole set with one click.

The "History" button shows the last seven days: date, mode, status, duration.


PORTABLE MODE
-------------

The archive whose name contains "portable" contains a file named "portable.flag". As long as
it is there, the data lives in a "data" folder next to the executable rather than in your
Windows profile: the program and your settings travel together on a USB stick.

Deleting "portable.flag" is enough to return to the normal mode — the existing data, however,
stays where it was written.


IF YOUR ANTIVIRUS BLOCKS IT
---------------------------

SecDailyBrief.exe is not code-signed, and a program that restarts itself to do its work
triggers several heuristic rules at once. Some scanners hold or block it on first launch.

Nothing is hidden in the file, and every release publishes the SHA256 of its archives.

- Add an exclusion for the folder that contains SecDailyBrief.exe. The scheduled task runs
  that same file, so one exclusion covers both the manual runs and the daily one.
- Or report a false positive to your vendor. For Avast:
  https://www.avast.com/false-positive-file-form.php
  This fixes it for every user, not only for you.


UNINSTALLING
------------

Run uninstall.ps1 (right-click, "Run with PowerShell"). It removes the scheduled task and
offers to delete the data. You can then delete this folder.


IF SOMETHING GOES WRONG
-----------------------

The "Diagnostic" button in the panel produces a report: eleven checks (engine, dependencies,
TLS certificates, data folder, settings, password, time zone, network, SMTP, scheduled task,
perimeter file). Paste it into your support request; it saves a lot of back and forth.

The full log can also be read in the panel, through the "Log" button.


LICENCE
-------

MIT — see LICENSE. Software provided without warranty.

Developed by Hormerty · © 2026
