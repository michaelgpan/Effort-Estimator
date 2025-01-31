class Task:
    def __init__(self, name, effort, description=""):
        self.name = name
        self.effort = effort
        self.description = description

class Module:
    def __init__(self, name):
        self.name = name
        self.tasks = []
        self._estimator = None  # Add this reference
        
    def add_task(self, task_name, effort, description=""):
        task = Task(task_name, effort, description)
        self.tasks.append(task)
        return task
        
    def get_total_effort(self):
        total = 0
        if hasattr(self, '_estimator') and self._estimator:
            # Find the subsystem that contains this module
            for subsystem in self._estimator.subsystems:
                if self in subsystem.modules:
                    subsystem_name = subsystem.name
                    # If module is disabled, return 0
                    if not self._estimator.module_states[subsystem_name].get(self.name, True):
                        return 0
                    # Calculate effort for all tasks
                    for task in self.tasks:
                        ratio = float(self._estimator.ui_vars[subsystem_name]['modules'][self.name]['tasks'][task.name]['ratio'].get()) / 100
                        total += task.effort * ratio
                    break
        else:
            # If no estimator reference, return raw sum
            total = sum(task.effort for task in self.tasks)
        return total

class Subsystem:
    def __init__(self, name):
        self.name = name
        self.modules = []
        self._estimator = None
        
    def add_module(self, module_name):
        module = Module(module_name)
        module._estimator = self._estimator  # Pass estimator reference
        self.modules.append(module)
        return module
        
    def get_total_effort(self):
        if not self._estimator or not self._estimator.module_states.get(self.name):
            return 0
        return sum(module.get_total_effort() for module in self.modules 
                  if self._estimator.module_states[self.name].get(module.name, True))

class EffortEstimator:
    def __init__(self, csv_file_path):
        self.subsystems = []
        self.subsystem_names = []
        self.subsystem_vars = {}
        self.module_vars = {}
        self.task_vars = {}
        self.task_labels = {}
        self.subsys_effort_labels = {}
        self.mod_effort_labels = {}
        self.subsystem_states = {}  # Store subsystem toggle states
        self.module_states = {}     # Store module toggle states
        self.task_states = {}       # Store task toggle states
        
        # Load data from CSV file
        self.load_data_from_csv(csv_file_path)
        
    def load_data_from_csv(self, csv_file_path):
        """Load system structure and effort data from CSV file"""
        import csv
        import os
        
        if not os.path.exists(csv_file_path):
            raise FileNotFoundError(f"CSV file not found: {csv_file_path}")
            
        # Use a dictionary to track created subsystems and modules
        subsystem_dict = {}
        module_dict = {}
        
        with open(csv_file_path, 'r', encoding='utf-8', newline='') as file:
            reader = csv.DictReader(file, 
                                  quoting=csv.QUOTE_MINIMAL,  # Use standard quoting
                                  quotechar='"',             # Specify quote character
                                  skipinitialspace=True)     # Skip spaces before fields
            for row in reader:
                subsystem_name = row['subsystem'].strip()
                module_name = row['module'].strip()
                task_name = row['task'].strip()
                effort = float(row['effort'])
                description = row['description'].strip()
                
                # If subsystem does not exist, create a new subsystem
                if subsystem_name not in subsystem_dict:
                    subsystem = self.add_subsystem(subsystem_name)
                    subsystem._estimator = self
                    subsystem_dict[subsystem_name] = subsystem
                    
                # Get the current subsystem
                subsystem = subsystem_dict[subsystem_name]
                
                # If module does not exist, create a new module
                module_key = f"{subsystem_name}_{module_name}"
                if module_key not in module_dict:
                    module = subsystem.add_module(module_name)
                    module_dict[module_key] = module
                    
                # Get the current module
                module = module_dict[module_key]
                
                # Create task with description information
                task = module.add_task(task_name, effort, description)
                # Initialize task state
                if subsystem_name not in self.task_states:
                    self.task_states[subsystem_name] = {}
                if module_name not in self.task_states[subsystem_name]:
                    self.task_states[subsystem_name][module_name] = {}
                self.task_states[subsystem_name][module_name][task_name] = True
        
    def add_subsystem(self, subsystem_name):
        subsystem = Subsystem(subsystem_name)
        subsystem._estimator = self  # Set estimator reference
        self.subsystems.append(subsystem)
        self.subsystem_names.append(subsystem_name)
        self.subsystem_states[subsystem_name] = True  # Default enabled
        self.module_states[subsystem_name] = {}       # Initialize the module state dictionary for this subsystem
        self.task_states[subsystem_name] = {}         # Initialize the task state dictionary for this subsystem
        return subsystem
        
    def get_total_effort(self):
        """Calculate total effort"""
        return sum(
            subsystem.get_total_effort()
            for subsystem in self.subsystems
            if self.subsystem_states.get(subsystem.name, True)
        )
        
    def display_summary(self):
        print("\nSoftware Effort Estimation Summary:")
        print("-" * 50)
        
        for subsystem in self.subsystems:
            if not self.subsystem_states.get(subsystem.name, True):
                continue
                
            print(f"\nSubsystem: {subsystem.name}")
            subsystem_effort = 0
            
            for module in subsystem.modules:
                if not self.module_states[subsystem.name].get(module.name, True):
                    continue
                    
                print(f"  Module: {module.name}")
                module_effort = 0
                
                for task in module.tasks:
                    if not self.task_states[subsystem.name].get(module.name, {}).get(task.name, True):
                        continue
                    
                    task_effort = task.effort
                    module_effort += task_effort
                    print(f"    Task: {task.name} - Effort: {task_effort}")
                
                print(f"  Module Total Effort: {module_effort}")
                subsystem_effort += module_effort
                
            print(f"Subsystem Total Effort: {subsystem_effort}")
            
        print(f"\nTotal Project Effort: {self.get_total_effort()}")

    def create_ui(self):
        import tkinter as tk
        from tkinter import ttk, messagebox
        
        self.root = tk.Tk()
        self.root.title("Effort Estimation Control Panel")
        
        # Initialize all required dictionaries
        self.ui_vars = {subsystem_name: {} for subsystem_name in self.subsystem_names}
        self.task_labels = {}
        self.mod_effort_labels = {}
        
        # Ensure all module states are properly initialized
        for subsystem_name in self.subsystem_names:
            self.mod_effort_labels[subsystem_name] = {}
            # Initialize subsystem variable
            self.ui_vars[subsystem_name]['var'] = tk.BooleanVar(value=True)
            self.ui_vars[subsystem_name]['modules'] = {}
            
            # Pre-initialize all module and task variables
            subsystem = next(s for s in self.subsystems if s.name == subsystem_name)
            for module in subsystem.modules:
                # Initialize module state
                if subsystem_name not in self.module_states:
                    self.module_states[subsystem_name] = {}
                self.module_states[subsystem_name][module.name] = True
                
                self.ui_vars[subsystem_name]['modules'][module.name] = {
                    'var': tk.BooleanVar(value=True),
                    'tasks': {}
                }
                for task in module.tasks:
                    self.ui_vars[subsystem_name]['modules'][module.name]['tasks'][task.name] = {
                        'ratio': tk.StringVar(value="100")
                    }
        
        # Create main frame
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Combined system view frame
        system_frame = ttk.LabelFrame(main_frame, text="System Hierarchy View")
        system_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Total effort display
        total_effort_frame = ttk.Frame(system_frame)
        total_effort_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(
            total_effort_frame,
            text="Total Project Effort:",
            font=('Arial', 12, 'bold')
        ).pack(side=tk.LEFT, padx=5)
        
        self.total_effort_value = ttk.Label(
            total_effort_frame,
            text=str(self.get_total_effort()),
            font=('Arial', 12, 'bold')
        )
        self.total_effort_value.pack(side=tk.LEFT, padx=5)
        
        # Create horizontally arranged subsystem container
        subsystems_container = ttk.Frame(system_frame)
        subsystems_container.pack(fill=tk.X, padx=5, pady=2)
        
        # Create a vertical frame for each subsystem
        for subsystem_name, subsystem in zip(self.subsystem_names, self.subsystems):
            # Create vertical frame for subsystem
            subsys_column = ttk.Frame(subsystems_container)
            subsys_column.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10)
            
            # Subsystem header frame
            subsys_header = ttk.Frame(subsys_column)
            subsys_header.pack(fill=tk.X)
            
            def make_subsystem_callback(s_name):
                return lambda: self.toggle_subsystem(s_name, self.ui_vars[s_name]['var'].get())
            
            # Subsystem checkbox and label
            subsys_cb = ttk.Checkbutton(
                subsys_header,
                text=f"{subsystem_name}",
                variable=self.ui_vars[subsystem_name]['var'],
                command=make_subsystem_callback(subsystem_name)
            )
            subsys_cb.pack(side=tk.LEFT)
            
            self.subsys_effort_labels[subsystem_name] = ttk.Label(
                subsys_header,
                text=f"(Total Effort: {subsystem.get_total_effort()})"
            )
            self.subsys_effort_labels[subsystem_name].pack(side=tk.LEFT, padx=5)
            
            # Module frame (with indentation)
            modules_frame = ttk.Frame(subsys_column)
            modules_frame.pack(fill=tk.X, padx=(20, 0))  # Left indent 20 pixels
            
            self.task_labels[subsystem_name] = {}
            
            # Vertically arrange modules
            for module in subsystem.modules:
                mod_name = module.name
                self.task_labels[subsystem_name][mod_name] = {}
                
                mod_var = tk.BooleanVar(value=True)
                self.ui_vars[subsystem_name]['modules'][mod_name]['var'] = mod_var
                
                def make_module_callback(s_name, m_name):
                    return lambda: self.toggle_module(s_name, m_name, 
                                                    self.ui_vars[s_name]['modules'][m_name]['var'].get())
                
                mod_frame = ttk.Frame(modules_frame)
                mod_frame.pack(fill=tk.X, pady=1)
                
                mod_cb = ttk.Checkbutton(
                    mod_frame,
                    text=f"{mod_name}",
                    variable=mod_var,
                    command=make_module_callback(subsystem_name, mod_name)
                )
                mod_cb.pack(side=tk.LEFT)
                
                self.mod_effort_labels[subsystem_name][mod_name] = ttk.Label(
                    mod_frame,
                    text=f"(Effort: {module.get_total_effort()})"
                )
                self.mod_effort_labels[subsystem_name][mod_name].pack(side=tk.LEFT)
        
        # Bottom frame: Task details
        bottom_frame = ttk.LabelFrame(main_frame, text="Task Details")
        bottom_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Create notebook widget
        self.notebook = ttk.Notebook(bottom_frame)  # Save as instance variable for access in other methods
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Save tab references for later use
        self.tabs = {}  # Add this dictionary to store tab references
        
        def create_scrollable_frame(parent):
            """Create a scrollable frame"""
            # Create container frame
            container = ttk.Frame(parent)
            container.pack(fill=tk.BOTH, expand=True)
            
            # Create canvas and scrollbar
            canvas = tk.Canvas(container)
            scrollbar = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
            scrollable_frame = ttk.Frame(canvas)
            
            # Configure scrolling
            def configure_scroll_region(event):
                canvas.configure(scrollregion=canvas.bbox("all"))
            
            scrollable_frame.bind("<Configure>", configure_scroll_region)
            
            # Create canvas window
            canvas_window = canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
            
            # Configure canvas size to change with window
            def configure_canvas(event):
                canvas.itemconfig(canvas_window, width=event.width)
            
            canvas.bind("<Configure>", configure_canvas)
            
            # Place canvas and scrollbar
            canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            
            # Configure canvas scrolling
            canvas.configure(yscrollcommand=scrollbar.set)
            
            # Configure mouse wheel scrolling
            def on_mousewheel(event):
                canvas.yview_scroll(int(-1*(event.delta/120)), "units")
            
            # Bind mouse wheel event
            scrollable_frame.bind("<MouseWheel>", on_mousewheel)
            canvas.bind("<MouseWheel>", on_mousewheel)
            
            return scrollable_frame, container
        
        # Create a tab for each subsystem
        for subsystem in self.subsystems:
            # Create tab
            tab = ttk.Frame(self.notebook)
            self.notebook.add(tab, text=subsystem.name)
            self.tabs[subsystem.name] = tab  # Save tab reference
            
            # Create scrollable frame
            scrollable_frame, _ = create_scrollable_frame(tab)
            
            # Display all modules and tasks of the subsystem in this tab
            for module in subsystem.modules:
                module_frame = ttk.LabelFrame(scrollable_frame, text=module.name)
                module_frame.pack(fill=tk.X, padx=5, pady=2, expand=True)
                
                self.task_labels[subsystem.name][module.name] = {}
                
                for task in module.tasks:
                    task_frame = ttk.Frame(module_frame)
                    task_frame.pack(fill=tk.X, padx=20, pady=1)
                    
                    # Remove checkbox variable, only use radio button variable
                    effort_ratio_var = tk.StringVar(value="100")  # Default select 100%
                    self.ui_vars[subsystem.name]['modules'][module.name]['tasks'][task.name] = {
                        'ratio': effort_ratio_var
                    }
                    
                    def make_ratio_callback(s_name, m_name, t_name):
                        def update_effort():
                            # Only update effort display when module is enabled
                            if self.module_states[s_name].get(m_name, True):
                                # Update total effort display
                                total = self.get_total_effort()
                                self.total_effort_value.configure(text=str(total))
                                
                                # Update subsystem effort display
                                subsystem = self.subsystems[self._get_subsystem_index(s_name)]
                                subsystem_effort = subsystem.get_total_effort()
                                self.subsys_effort_labels[s_name].configure(
                                    text=f"(Total Effort: {subsystem_effort})"
                                )
                            
                            # Always update module effort display (but will show as 0 if module is disabled)
                            module = self.subsystems[self._get_subsystem_index(s_name)].modules[self._get_module_index(s_name, m_name)]
                            module_effort = module.get_total_effort()
                            self.mod_effort_labels[s_name][m_name].configure(
                                text=f"(Effort: {module_effort})"
                            )
                        return update_effort
                    
                    # Task name label
                    ttk.Label(
                        task_frame,
                        text=task.name
                    ).grid(row=0, column=0, sticky='w', padx=(0, 10))
                    
                    # Create radio button frame
                    radio_frame = ttk.Frame(task_frame)
                    radio_frame.grid(row=0, column=1, padx=(0, 10))
                    
                    # Add four radio buttons
                    for ratio, text in [("100", "100%"), ("60", "60%"), ("25", "25%"), ("0", "0%")]:
                        ttk.Radiobutton(
                            radio_frame,
                            text=text,
                            variable=effort_ratio_var,
                            value=ratio,
                            command=make_ratio_callback(subsystem.name, module.name, task.name)
                        ).pack(side=tk.LEFT, padx=2)
                    
                    # Effort label
                    effort_label = ttk.Label(
                        task_frame,
                        text=f"(Effort: {task.effort})"
                    )
                    effort_label.grid(row=0, column=2, padx=(0, 10))
                    
                    # Separator
                    ttk.Label(task_frame, text="-").grid(row=0, column=3, padx=5)
                    
                    # Description text
                    description_label = ttk.Label(
                        task_frame,
                        text=task.description,
                        justify=tk.LEFT,
                        wraplength=800
                    )
                    description_label.grid(row=0, column=4, sticky='w', padx=5)
                    
                    # Configure column width and weight
                    task_frame.grid_columnconfigure(0, minsize=150)  # Task name column
                    task_frame.grid_columnconfigure(1, minsize=150)  # Radio button column
                    task_frame.grid_columnconfigure(2, minsize=100)  # Effort column
                    task_frame.grid_columnconfigure(3, minsize=20)   # Separator column
                    task_frame.grid_columnconfigure(4, weight=1)     # Description text column can expand
                    
                    # Save effort label reference
                    self.task_labels[subsystem.name][module.name][task.name] = effort_label
                    effort_label.bind('<Double-Button-1>',
                        lambda e, s=subsystem.name, m=module.name, t=task:
                        self.edit_task_effort(s, m, t))
        
        # Set minimum size for main window
        self.root.update()
        min_width = max(800, self.root.winfo_width())
        min_height = max(600, self.root.winfo_height())
        self.root.minsize(min_width, min_height)
        
        # Set initial window size
        self.root.geometry(f"{min_width}x{min_height}")
        
        # Add visualization tab
        self.create_visualization_tab()
    
    def toggle_subsystem(self, subsystem_name, state):
        """Handle when a subsystem is selected or deselected"""
        self.subsystem_states[subsystem_name] = state
        
        # Switch to the corresponding tab
        tab_id = self.notebook.tabs().index(str(self.tabs[subsystem_name]))
        self.notebook.select(tab_id)
        
        # Update UI and internal state
        for module_name in self.module_states[subsystem_name]:
            # Update module state
            self.module_states[subsystem_name][module_name] = state
            self.ui_vars[subsystem_name]['modules'][module_name]['var'].set(state)
            
            # Update task state
            for task_name in self.ui_vars[subsystem_name]['modules'][module_name]['tasks']:
                self.ui_vars[subsystem_name]['modules'][module_name]['tasks'][task_name]['ratio'].set("100" if state else "0")
        
        # Update summary information
        self.get_summary()

    def toggle_module(self, subsystem_name, module_name, state):
        """Handle when a module is selected or deselected"""
        # Switch to the corresponding tab
        tab_id = self.notebook.tabs().index(str(self.tabs[subsystem_name]))
        self.notebook.select(tab_id)
        
        # Ensure module state dictionary exists
        if subsystem_name not in self.module_states:
            self.module_states[subsystem_name] = {}
        self.module_states[subsystem_name][module_name] = state
        
        # Update all task radio button states
        for task_name in self.ui_vars[subsystem_name]['modules'][module_name]['tasks']:
            ratio_var = self.ui_vars[subsystem_name]['modules'][module_name]['tasks'][task_name]['ratio']
            ratio_var.set("100" if state else "0")
        
        # When the module is enabled, ensure its parent subsystem is enabled
        if state:
            self.subsystem_states[subsystem_name] = True
            self.ui_vars[subsystem_name]['var'].set(True)
        # Check if the subsystem needs to be disabled
        else:
            # Safely check all module states
            all_modules_disabled = all(
                not self.module_states.get(subsystem_name, {}).get(mod.name, True)
                for mod in self.subsystems[self._get_subsystem_index(subsystem_name)].modules
            )
            if all_modules_disabled:
                self.subsystem_states[subsystem_name] = False
                self.ui_vars[subsystem_name]['var'].set(False)
        
        # Update total effort display
        self.total_effort_value.configure(text=str(self.get_total_effort()))
        
        # Update subsystem effort display
        self.subsys_effort_labels[subsystem_name].configure(
            text=f"(Total Effort: {self.subsystems[self._get_subsystem_index(subsystem_name)].get_total_effort()})"
        )
        
        # Update module effort display
        module_effort = self.subsystems[self._get_subsystem_index(subsystem_name)].modules[self._get_module_index(subsystem_name, module_name)].get_total_effort()
        self.mod_effort_labels[subsystem_name][module_name].configure(
            text=f"(Effort: {module_effort})"
        )

    def toggle_task(self, subsystem_name, module_name, task_name, state):
        self.task_states[subsystem_name][module_name][task_name] = state
        
        # When the task is enabled, ensure its parent module and subsystem are enabled
        if state:
            self.subsystem_states[subsystem_name] = True
            self.module_states[subsystem_name][module_name] = True
            self.ui_vars[subsystem_name]['var'].set(True)
            self.ui_vars[subsystem_name]['modules'][module_name]['var'].set(True)
        # Check if the module and subsystem need to be disabled
        else:
            all_tasks_disabled = all(not self.task_states[subsystem_name][module_name][task.name] 
                                   for task in self.subsystems[self._get_subsystem_index(subsystem_name)]
                                   .modules[self._get_module_index(subsystem_name, module_name)].tasks)
            if all_tasks_disabled:
                self.module_states[subsystem_name][module_name] = False
                self.ui_vars[subsystem_name]['modules'][module_name]['var'].set(False)
                
                # Check if the subsystem needs to be disabled
                all_modules_disabled = all(not self.module_states[subsystem_name][mod.name] 
                                         for mod in self.subsystems[self._get_subsystem_index(subsystem_name)].modules)
                if all_modules_disabled:
                    self.subsystem_states[subsystem_name] = False
                    self.ui_vars[subsystem_name]['var'].set(False)
        
        # Update summary information
        self.get_summary()

    def _get_subsystem_index(self, subsystem_name):
        """Helper method: Get subsystem index"""
        for i, subsystem in enumerate(self.subsystems):
            if subsystem.name == subsystem_name:
                return i
        return -1

    def _get_module_index(self, subsystem_name, module_name):
        """Helper method: Get module index"""
        subsystem = self.subsystems[self._get_subsystem_index(subsystem_name)]
        for i, module in enumerate(subsystem.modules):
            if module.name == module_name:
                return i
        return -1

    def add_module_to_subsystem(self, subsystem_name, module):
        """Initialize its state when adding a module"""
        self.module_states[subsystem_name][module.name] = True
        self.task_states[subsystem_name][module.name] = {}
        return module

    def edit_task_effort(self, subsystem_name, module_name, task):
        """Edit task effort dialog"""
        dialog = tk.Toplevel()
        dialog.title(f"Edit Effort - {task.name}")
        dialog.geometry("300x150")
        dialog.transient(dialog.master)
        dialog.grab_set()
        
        # Center display
        dialog.geometry("+%d+%d" % (
            dialog.master.winfo_rootx() + dialog.master.winfo_width()/2 - 150,
            dialog.master.winfo_rooty() + dialog.master.winfo_height()/2 - 75
        ))
        
        # Create input box and label
        ttk.Label(dialog, text=f"Enter new effort for {task.name}:").pack(pady=10)
        effort_var = tk.StringVar(value=str(task.effort))
        entry = ttk.Entry(dialog, textvariable=effort_var)
        entry.pack(pady=5)
        entry.select_range(0, tk.END)
        entry.focus()
        
        def validate_and_save():
            try:
                new_effort = float(effort_var.get())
                if new_effort < 0:
                    raise ValueError("Effort cannot be negative")
                task.effort = new_effort
                # Update UI display
                self.task_labels[subsystem_name][module_name][task.name].configure(
                    text=f"(Effort: {new_effort})"
                )
                # Update all related effort displays
                self.update_all_effort_labels(subsystem_name, module_name)
                dialog.destroy()
            except ValueError as e:
                tk.messagebox.showerror("Error", "Please enter a valid number!")
                entry.focus()
        
        def cancel():
            dialog.destroy()
        
        # Create button frame
        button_frame = ttk.Frame(dialog)
        button_frame.pack(pady=20)
        
        ttk.Button(button_frame, text="OK", command=validate_and_save).pack(side=tk.LEFT, padx=10)
        ttk.Button(button_frame, text="Cancel", command=cancel).pack(side=tk.LEFT)
        
        # Bind Enter key to OK button
        dialog.bind('<Return>', lambda e: validate_and_save())
        # Bind Escape key to Cancel button
        dialog.bind('<Escape>', lambda e: cancel())

    def update_all_effort_labels(self, subsystem_name, module_name):
        """Update all related effort labels"""
        # Update module effort
        module = self.subsystems[self._get_subsystem_index(subsystem_name)].modules[self._get_module_index(subsystem_name, module_name)]
        self.mod_effort_labels[subsystem_name][module_name].configure(
            text=f"(Effort: {module.get_total_effort()})"
        )
        
        # Update subsystem effort
        subsystem = self.subsystems[self._get_subsystem_index(subsystem_name)]
        self.subsys_effort_labels[subsystem_name].configure(
            text=f"(Total Effort: {subsystem.get_total_effort()})"
        )
        
        # Update total project effort
        self.total_effort_value.configure(text=str(self.get_total_effort()))

    def get_summary(self):
        """Update all effort displays"""
        # Update total effort
        self.total_effort_value.configure(text=str(self.get_total_effort()))
        
        # Update each subsystem's effort
        for subsystem in self.subsystems:
            self.subsys_effort_labels[subsystem.name].configure(
                text=f"(Total Effort: {subsystem.get_total_effort()})"
            )
            # Update effort for each module under this subsystem
            for module in subsystem.modules:
                self.mod_effort_labels[subsystem.name][module.name].configure(
                    text=f"(Effort: {module.get_total_effort()})"
                )

    def create_visualization_tab(self):
        """Create visualization tab"""
        import matplotlib.pyplot as plt
        from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
        from matplotlib.figure import Figure
        import tkinter as tk
        from tkinter import ttk  # Add this line import
        
        # Create visualization tab
        viz_tab = ttk.Frame(self.notebook)
        self.notebook.add(viz_tab, text="Visualization")
        
        # Create left and right frames
        left_frame = ttk.Frame(viz_tab)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        right_frame = ttk.Frame(viz_tab)
        right_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Create pie chart
        def create_subsystem_pie():
            # Collect data
            labels = []
            sizes = []
            for subsystem in self.subsystems:
                if self.subsystem_states.get(subsystem.name, True):
                    effort = subsystem.get_total_effort()
                    if effort > 0:  # Only show non-zero effort
                        labels.append(subsystem.name)
                        sizes.append(effort)
            
            # Create pie chart
            fig = Figure(figsize=(6, 4))
            ax = fig.add_subplot(111)
            ax.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=90)
            ax.axis('equal')
            ax.set_title('Subsystem Effort Distribution')
            
            return fig
        
        def create_module_bar():
            # Collect data
            modules = []
            efforts = []
            colors = []
            
            for subsystem in self.subsystems:
                if self.subsystem_states.get(subsystem.name, True):
                    for module in subsystem.modules:
                        if self.module_states[subsystem.name].get(module.name, True):
                            effort = module.get_total_effort()
                            if effort > 0:  # Only show non-zero effort
                                modules.append(f"{subsystem.name}\n{module.name}")
                                efforts.append(effort)
                                colors.append(plt.cm.Set3(len(modules) % 12))
            
            # Create bar chart
            fig = Figure(figsize=(6, 4))
            ax = fig.add_subplot(111)
            bars = ax.bar(range(len(modules)), efforts, color=colors)
            ax.set_xticks(range(len(modules)))
            ax.set_xticklabels(modules, rotation=45, ha='right')
            ax.set_title('Module Effort Comparison')
            ax.set_ylabel('Effort')
            
            # Add value labels
            for bar in bars:
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2., height,
                       f'{int(height)}',
                       ha='center', va='bottom')
            
            fig.tight_layout()
            return fig
        
        # Create chart display area
        pie_canvas = FigureCanvasTkAgg(create_subsystem_pie(), left_frame)
        pie_canvas.draw()
        pie_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        bar_canvas = FigureCanvasTkAgg(create_module_bar(), right_frame)
        bar_canvas.draw()
        bar_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        # Add refresh button
        def refresh_charts():
            # Clear old charts
            for widget in left_frame.winfo_children():
                widget.destroy()
            for widget in right_frame.winfo_children():
                widget.destroy()
            
            # Create new charts
            pie_canvas = FigureCanvasTkAgg(create_subsystem_pie(), left_frame)
            pie_canvas.draw()
            pie_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
            
            bar_canvas = FigureCanvasTkAgg(create_module_bar(), right_frame)
            bar_canvas.draw()
            bar_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
            
            # Ensure refresh button is only added once
            if not refresh_button.winfo_ismapped():
                refresh_button.pack(pady=5)
        
        ttk.Button(viz_tab, text="Refresh Charts", command=refresh_charts).pack(pady=5)

# Modify main program entry
if __name__ == "__main__":
    # Use CSV file to initialize estimator
    estimator = EffortEstimator("effort_data.csv")
    # Start UI interface
    estimator.create_ui()
    # Call mainloop here
    estimator.root.mainloop()
