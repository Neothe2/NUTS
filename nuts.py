import os
import subprocess
from textual import on, events
from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Label, Input, OptionList, RichLog, SelectionList
from textual.widgets.option_list import Option
from textual.containers import Horizontal, Vertical

# --- TEMPLATE DEFINITIONS ---
DOTNET_TEMPLATES = {
    "console": {
        "display": "Console Application",
        "flags": [("--use-program-main", "Use explicit Program.Main()")]
    },
    "webapi": {
        "display": "ASP.NET Core Web API",
        "flags": [
            ("--use-program-main", "Use explicit Program.Main()"),
            ("--use-controllers", "Use Controllers (no minimal APIs)"),
            ("--no-openapi", "Disable OpenAPI/Swagger"),
            ("--no-https", "Disable HTTPS redirection")
        ]
    },
    "mvc": {
        "display": "ASP.NET Core Web App (MVC)",
        "flags": [
            ("--use-program-main", "Use explicit Program.Main()"),
            ("--no-https", "Disable HTTPS redirection")
        ]
    },
    "classlib": {
        "display": "Class Library",
        "flags": []
    }
}

class NutsApp(App):
    """N.U.T.S. - Lazygit style .NET creator"""
    
    CSS = """
    Screen { background: $surface-darken-3; }
    
    #top-panes { height: 70%; }
    #bottom-pane { height: 30%; margin-top: 1; }
    
    .pane { 
        width: 1fr; 
        height: 100%; 
        border: round $primary-muted; 
        border-title-color: $text-muted;
        background: $panel;
        padding: 0 1;
        transition: border 200ms;
    }
    
    /* NORMAL MODE: Blue/Green Glow */
    .pane:focus-within { 
        border: heavy $accent; 
        border-title-color: $accent;
        background: $surface;
    }
    
    /* INSERT MODE: Warning/Yellow Glow for text inputs */
    #pane1-names:focus-within {
        border: heavy $warning;
        border-title-color: $warning;
    }
    
    #pane1-names { width: 0.8fr; }
    #pane2-templates { width: 1.2fr; }
    #pane3-options { width: 1.2fr; }
    
    Input { margin-top: 1; margin-bottom: 2; border: tall $primary-muted; }
    Input:focus { border: tall $warning; }
    OptionList, SelectionList { background: transparent; border: none; }
    RichLog { background: #0c0c0c; color: #00ff00; padding: 0 1; }
    .help-text { color: $text-muted; text-align: center; margin-top: 2; }
    """

    # Removed hjkl from here so they don't break text typing!
    BINDINGS = [
        ("q", "quit", "Quit"),
        ("c", "create", "Execute Command"),
        ("escape", "escape_input", "Normal Mode (Esc)"),
        ("1", "focus_pane1", "Pane 1"),
        ("2", "focus_pane2", "Pane 2"),
        ("3", "focus_pane3", "Pane 3"),
    ]

    def __init__(self):
        super().__init__()
        self.selected_template_key = "console"

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        
        with Vertical():
            with Horizontal(id="top-panes"):
                with Vertical(id="pane1-names", classes="pane"):
                    yield Label("1. Details", classes="help-text")
                    yield Label("Solution Name:")
                    yield Input(placeholder="e.g. AcmeCorp", id="sln_name")
                    yield Label("Project Name:")
                    yield Input(placeholder="e.g. AcmeCorp.Api", id="proj_name")
                    yield Label("[bold]Ready?[/]\nPress 'c' to build.", markup=True, classes="help-text")
                
                with Vertical(id="pane2-templates", classes="pane"):
                    yield Label("2. Templates", classes="help-text")
                    template_list = OptionList(id="template_list")
                    for key, data in DOTNET_TEMPLATES.items():
                        template_list.add_option(Option(data["display"], id=key))
                    yield template_list
                
                with Vertical(id="pane3-options", classes="pane"):
                    yield Label("3. Options ([Space] to toggle)", classes="help-text")
                    yield SelectionList(id="flag_list")

            with Vertical(id="bottom-pane", classes="pane") as log_pane:
                log_pane.border_title = "Execution Log"
                yield RichLog(id="terminal_log", highlight=True, markup=True)
                
        yield Footer()

    def on_mount(self) -> None:
        self.update_flags("console")
        self.log_message("[bold blue]N.U.T.S initialized.[/]")
        self.log_message("Navigate with [bold]h/l[/] or [bold]1/2/3[/]. Toggle flags with [bold]Space[/]. Press [bold]c[/] to create.")
        self.action_focus_pane2()

    # --- TRUE VIM MODE ROUTER ---
    
    def on_key(self, event: events.Key) -> None:
        """Intercepts key presses before they do anything else."""
        
        # INSERT MODE: If focused on a text box, let the user type freely!
        if isinstance(self.focused, Input):
            return

        # NORMAL MODE: Safe to use Vim motions
        if event.character == "h":
            self.action_focus_left()
        elif event.character == "l":
            self.action_focus_right()
        # Note: 'j' and 'k' scroll natively inside the Option/Selection lists!
        # If we intercepted them here, the lists would break.

    # --- PANE NAVIGATION LOGIC ---
    
    def get_current_pane_index(self) -> int:
        focused = self.focused
        if not focused: return 2
        if focused.id in ["sln_name", "proj_name"]: return 1
        if focused.id == "template_list": return 2
        if focused.id == "flag_list": return 3
        return 2

    def action_focus_left(self):
        idx = self.get_current_pane_index()
        if idx == 3: self.action_focus_pane2()
        elif idx == 2: self.action_focus_pane1()

    def action_focus_right(self):
        idx = self.get_current_pane_index()
        if idx == 1: self.action_focus_pane2()
        elif idx == 2: self.action_focus_pane3()

    def action_focus_pane1(self):
        self.query_one("#sln_name").focus()

    def action_focus_pane2(self):
        self.query_one("#template_list").focus()

    def action_focus_pane3(self):
        self.query_one("#flag_list").focus()

    def action_escape_input(self):
        """Drops you out of Insert Mode back to Normal Mode."""
        self.action_focus_pane2()

    # --- APP LOGIC ---

    @on(OptionList.OptionHighlighted, "#template_list")
    def handle_template_highlight(self, event: OptionList.OptionHighlighted) -> None:
        self.selected_template_key = event.option.id
        self.update_flags(self.selected_template_key)

    def update_flags(self, template_key: str):
        flag_list = self.query_one("#flag_list", SelectionList)
        flag_list.clear_options()
        
        flags = DOTNET_TEMPLATES.get(template_key, {}).get("flags", [])
        if not flags:
            flag_list.add_option(("No options available", "none"))
            flag_list.disabled = True
        else:
            flag_list.disabled = False
            flag_list.add_options([(display, cli_flag) for cli_flag, display in flags])

    def action_create(self) -> None:
        sln_name = self.query_one("#sln_name", Input).value.strip()
        proj_name = self.query_one("#proj_name", Input).value.strip()

        if not sln_name or not proj_name:
            self.log_message("\n[bold red]Error:[/] You must provide a Solution Name and Project Name in Pane 1!")
            self.app.bell()
            self.action_focus_pane1()
            return

        template = self.selected_template_key
        flags = self.query_one("#flag_list", SelectionList).selected
        flags = [f for f in flags if f != "none"]

        self.log_message(f"\n[bold green]--- Creating {sln_name} ---[/]")

        try:
            self.run_cmd(["dotnet", "new", "sln", "-n", sln_name, "-o", sln_name])
            
            proj_path = os.path.join(sln_name, proj_name)
            cmd = ["dotnet", "new", template, "-n", proj_name, "-o", proj_path] + flags
            self.run_cmd(cmd)
            
            sln_file = os.path.join(sln_name, f"{sln_name}.sln")
            proj_file = os.path.join(proj_path, f"{proj_name}.csproj")
            self.run_cmd(["dotnet", "sln", sln_file, "add", proj_file])
            
            self.log_message(f"[bold green]Success![/] Solution [bold]{sln_name}[/] is ready.")
            
        except subprocess.CalledProcessError as e:
            self.log_message(f"[bold red]Command failed with exit code {e.returncode}[/]")

    def run_cmd(self, cmd_list: list[str]) -> None:
        cmd_str = " ".join(cmd_list)
        self.log_message(f"> [cyan]{cmd_str}[/]")
        
        result = subprocess.run(cmd_list, capture_output=True, text=True)
        if result.stdout:
            self.log_message(result.stdout.strip())
        if result.stderr:
            self.log_message(f"[red]{result.stderr.strip()}[/]")
            
        if result.returncode != 0:
            raise subprocess.CalledProcessError(result.returncode, cmd_list)

    def log_message(self, message: str) -> None:
        log = self.query_one("#terminal_log", RichLog)
        log.write(message)

if __name__ == "__main__":
    app = NutsApp()
    app.run()
