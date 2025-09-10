# Survey Results Previewer

A PyQt desktop application for analyzing and reporting on survey data from the VOXCO platform.

## Features
- Import survey data from _.db, .csv, .xlsx_ formats
- Interactive table preview with clickable filtering
- Advanced text-based filtering syntax
- Export to HTML reports and database files
- Supports multiple question types including _RadioButton, CheckBox, Grids, Ranking,_ etc.

## Note
This is a _legacy_ application built with Python 2.7 and PyQt. It's maintained for historical reference.

## ⚠️ Legacy Notice
This project was built with Python 2.7 (EOL) and may contain outdated patterns. It's uploaded for:
- Historical reference
- Educational purposes
- Demonstration of domain-specific data processing

## Details
This is a **distributable** (runs in any Windows machine with no python installation required), **portable** (no app installation required), **standalone** application (run by single executable) written in Python which is used for monitoring surveys hosted by VOXCO platform.

The application provides a local environment, outside the VOXCO survey hosting platform, where the user can preview in a flexible, clean and compact way the survey results, perform complex filters on survey data and export (filtered) database files or static html previews for future use.

Through the GUI the user can filter the data either by typing expressions which are parsed internally by the application or interact with the previewing environment by clicking on the hyperlinked reporting table numbers.

## Tools
Libraries used include ***PyQt4, json, xlrd, csv, HTMLParser, PyInstaller***

## Usage

- ***Import***: Use the top menu to first import a Questionnaire file _(.db/.xlsx)_, then a Data file _(.db/.csv/.xlsx)_.
- ***Preview & Filter***:
    - Select questions from the list and click _"Preview Selected"_.
    - Apply filters either by clicking on table values or by typing expressions in the _"Filters"_ textbox (see documentation below for syntax).
- ***Export***: Export the filtered results as static HTML reports or new database (.db) files for further analysis.

## Documentation
Detailed documentation on all the supported features can be found [here](./docs/SRP_docs.pdf)

## Demos
### Importing Questionnaire Files
This video shows the first step: loading the questionnaire structure file.

This file defines the questions, their types, and answer choices, which the application uses to correctly interpret and display the survey data.
<p align="center"><video width="800" controls><source src="./resources/videos/01-Importing-Questionnaire-Files.mp4" type="video/mp4"></video></p>

### Importing Data Files
This video demonstrates loading the actual survey response data.

The application supports multiple formats, and once loaded, the imported questionnaire matches with the data, the current base appears on the output text box, and results are ready for preview.
<p align="center"><video width="800" controls><source src="./resources/videos/02-Importing-Data-Files.mp4" type="video/mp4"></video></p>

### Preview and Navigate Results
Here, we generate an interactive HTML preview of selected questions. The left-hand table of contents with hyperlinks to questions allows for easy navigation through a potentially large set of results.
<p align="center"><video width="800" controls><source src="./resources/videos/03-Preview-and-Navigate-Results.mp4" type="video/mp4"></video></p>

### Apply/Remove Interactive Filters
This demo highlights the powerful interactive filtering feature. By clicking on the hyperlinked values (counts or table bases) within the HTML tables, users can drill down into specific data subsets.

The interface shows the applied filter and allows stepping back through the filter history.
<p align="center"><video width="800" controls><source src="./resources/videos/04-Apply-Remove-Interactive-Filters.mp4" type="video/mp4"></video></p>

### Apply/Remove Parsed Filters
This video showcases the advanced text-based filtering syntax.

Users can type complex logical expressions (e.g., `∽RB_1:1 & (CG_2:[1.3..5] | NA_3:>100)`) to perform precise, multi-layered data segmentation that could not be achieved through clicking alone.
<p align="center"><video width="800" controls><source src="./resources/videos/05-Apply-Remove-Parsed-Filters.mp4" type="video/mp4"></video></p>

### Export HTML Previews
Once the data is filtered to the desired subset, this feature allows exporting the current preview as a static HTML report. This is ideal for sharing specific insights with others who may not have the application.
<p align="center"><video width="800" controls><source src="./resources/videos/06-Export-HTML-Previews.mp4" type="video/mp4"></video></p>

### Export (Filtered) Data
The most powerful export feature: saving the filtered dataset itself as a new .db file. This allows for further analysis on the specific data segment in other tools or for re-importing later into this application, preserving all applied filters.
<p align="center"><video width="800" controls><source src="./resources/videos/07-Export-Filtered-Data.mp4" type="video/mp4"></video></p>