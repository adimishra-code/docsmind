# Theme Rules

## Overview
The platform supports Dark, Light, and System themes using `next-themes` and standard Tailwind CSS variables.

## Token Usage
Do not use raw color tokens like `text-slate-900` or `bg-blue-500`.
Instead, use semantic tokens:
- `bg-background` (Page background)
- `bg-card` (Elevated surfaces)
- `text-foreground` (Primary text)
- `text-muted-foreground` (Secondary text)
- `bg-primary text-primary-foreground` (Primary buttons)

## Theme Switching
Theme switching is handled by `ThemeProvider` wrapping the application root.
It injects the `.dark` class onto the `<html>` element based on user preference or `(prefers-color-scheme: dark)`.
