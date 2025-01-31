class Task:
    def __init__(self, name, effort, description=""):
        self.name = name
        self.effort = effort
        self.description = description

class Module:
    def __init__(self, name):
        self.name = name
        self.tasks = []
        self._estimator = None  # 添加这个引用
        
    def add_task(self, task_name, effort, description=""):
        task = Task(task_name, effort, description)
        self.tasks.append(task)
        return task
        
    def get_total_effort(self):
        total = 0
        if hasattr(self, '_estimator') and self._estimator:
            # 找到该模块所属的子系统
            for subsystem in self._estimator.subsystems:
                if self in subsystem.modules:
                    subsystem_name = subsystem.name
                    # 如果模块被禁用，直接返回0
                    if not self._estimator.module_states[subsystem_name].get(self.name, True):
                        return 0
                    # 计算所有任务的工作量
                    for task in self.tasks:
                        ratio = float(self._estimator.ui_vars[subsystem_name]['modules'][self.name]['tasks'][task.name]['ratio'].get()) / 100
                        total += task.effort * ratio
                    break
        else:
            # 如果没有 estimator 引用，直接返回总和
            total = sum(task.effort for task in self.tasks)
        return total

class Subsystem:
    def __init__(self, name):
        self.name = name
        self.modules = []
        self._estimator = None
        
    def add_module(self, module_name):
        module = Module(module_name)
        module._estimator = self._estimator  # 传递 estimator 引用
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
        self.subsystem_states = {}  # 存储子系统的开关状态
        self.module_states = {}     # 存储模块的开关状态
        self.task_states = {}       # 存储任务的开关状态
        
        # 从CSV文件加载数据
        self.load_data_from_csv(csv_file_path)
        
    def load_data_from_csv(self, csv_file_path):
        """从CSV文件加载系统结构和工作量数据"""
        import csv
        import os
        
        if not os.path.exists(csv_file_path):
            raise FileNotFoundError(f"找不到CSV文件: {csv_file_path}")
            
        # 使用字典来跟踪已创建的子系统和模块
        subsystem_dict = {}
        module_dict = {}
        
        with open(csv_file_path, 'r', encoding='utf-8', newline='') as file:
            reader = csv.DictReader(file, 
                                  quoting=csv.QUOTE_MINIMAL,  # 使用标准引号处理
                                  quotechar='"',             # 指定引号字符
                                  skipinitialspace=True)     # 跳过字段前的空格
            for row in reader:
                subsystem_name = row['subsystem'].strip()
                module_name = row['module'].strip()
                task_name = row['task'].strip()
                effort = float(row['effort'])
                description = row['description'].strip()
                
                # 如果子系统不存在，创建新的子系统
                if subsystem_name not in subsystem_dict:
                    subsystem = self.add_subsystem(subsystem_name)
                    subsystem._estimator = self
                    subsystem_dict[subsystem_name] = subsystem
                    
                # 获取当前子系统
                subsystem = subsystem_dict[subsystem_name]
                
                # 如果模块不存在，创建新的模块
                module_key = f"{subsystem_name}_{module_name}"
                if module_key not in module_dict:
                    module = subsystem.add_module(module_name)
                    module_dict[module_key] = module
                    
                # 获取当前模块
                module = module_dict[module_key]
                
                # 创建任务时包含描述信息
                task = module.add_task(task_name, effort, description)
                # 初始化任务状态
                if subsystem_name not in self.task_states:
                    self.task_states[subsystem_name] = {}
                if module_name not in self.task_states[subsystem_name]:
                    self.task_states[subsystem_name][module_name] = {}
                self.task_states[subsystem_name][module_name][task_name] = True
        
    def add_subsystem(self, subsystem_name):
        subsystem = Subsystem(subsystem_name)
        subsystem._estimator = self  # 设置 estimator 引用
        self.subsystems.append(subsystem)
        self.subsystem_names.append(subsystem_name)
        self.subsystem_states[subsystem_name] = True  # 默认开启
        self.module_states[subsystem_name] = {}       # 初始化该子系统的模块状态字典
        self.task_states[subsystem_name] = {}         # 初始化该子系统的任务状态字典
        return subsystem
        
    def get_total_effort(self):
        """计算总工作量"""
        return sum(
            subsystem.get_total_effort()
            for subsystem in self.subsystems
            if self.subsystem_states.get(subsystem.name, True)
        )
        
    def display_summary(self):
        print("\n软件工作量估算汇总:")
        print("-" * 50)
        
        for subsystem in self.subsystems:
            if not self.subsystem_states.get(subsystem.name, True):
                continue
                
            print(f"\n子系统: {subsystem.name}")
            subsystem_effort = 0
            
            for module in subsystem.modules:
                if not self.module_states[subsystem.name].get(module.name, True):
                    continue
                    
                print(f"  模块: {module.name}")
                module_effort = 0
                
                for task in module.tasks:
                    if not self.task_states[subsystem.name].get(module.name, {}).get(task.name, True):
                        continue
                    
                    task_effort = task.effort
                    module_effort += task_effort
                    print(f"    任务: {task.name} - 工作量: {task_effort}")
                
                print(f"  模块总工作量: {module_effort}")
                subsystem_effort += module_effort
                
            print(f"子系统总工作量: {subsystem_effort}")
            
        print(f"\n总工作量: {self.get_total_effort()}")

    def create_ui(self):
        import tkinter as tk
        from tkinter import ttk, messagebox
        
        self.root = tk.Tk()
        self.root.title("Effort Estimation Control Panel")
        
        # 初始化所有需要的字典
        self.ui_vars = {subsystem_name: {} for subsystem_name in self.subsystem_names}
        self.task_labels = {}
        self.mod_effort_labels = {}
        
        # 确保所有模块状态都被正确初始化
        for subsystem_name in self.subsystem_names:
            self.mod_effort_labels[subsystem_name] = {}
            # 初始化子系统变量
            self.ui_vars[subsystem_name]['var'] = tk.BooleanVar(value=True)
            self.ui_vars[subsystem_name]['modules'] = {}
            
            # 预先初始化所有模块和任务的变量
            subsystem = next(s for s in self.subsystems if s.name == subsystem_name)
            for module in subsystem.modules:
                # 初始化模块状态
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
        
        # 创建主框架
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 合并的系统视图框架
        system_frame = ttk.LabelFrame(main_frame, text="System Hierarchy View")
        system_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # 总工作量显示
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
        
        # 创建水平排列的子系统容器
        subsystems_container = ttk.Frame(system_frame)
        subsystems_container.pack(fill=tk.X, padx=5, pady=2)
        
        # 为每个子系统创建一个垂直框架
        for subsystem_name, subsystem in zip(self.subsystem_names, self.subsystems):
            # 创建子系统的垂直框架
            subsys_column = ttk.Frame(subsystems_container)
            subsys_column.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10)
            
            # 子系统标题框架
            subsys_header = ttk.Frame(subsys_column)
            subsys_header.pack(fill=tk.X)
            
            def make_subsystem_callback(s_name):
                return lambda: self.toggle_subsystem(s_name, self.ui_vars[s_name]['var'].get())
            
            # 子系统复选框和标签
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
            
            # 模块框架（带缩进）
            modules_frame = ttk.Frame(subsys_column)
            modules_frame.pack(fill=tk.X, padx=(20, 0))  # 左侧缩进20像素
            
            self.task_labels[subsystem_name] = {}
            
            # 垂直排列模块
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
        
        # 底部框架：任务详情
        bottom_frame = ttk.LabelFrame(main_frame, text="Task Details")
        bottom_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 创建标签页控件
        self.notebook = ttk.Notebook(bottom_frame)  # 保存为实例变量以便其他方法访问
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 保存标签页引用以便后续使用
        self.tabs = {}  # 添加这个字典来存储标签页引用
        
        def create_scrollable_frame(parent):
            """创建一个带滚动条的框架"""
            # 创建容器框架
            container = ttk.Frame(parent)
            container.pack(fill=tk.BOTH, expand=True)
            
            # 创建画布和滚动条
            canvas = tk.Canvas(container)
            scrollbar = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
            scrollable_frame = ttk.Frame(canvas)
            
            # 配置滚动
            def configure_scroll_region(event):
                canvas.configure(scrollregion=canvas.bbox("all"))
            
            scrollable_frame.bind("<Configure>", configure_scroll_region)
            
            # 创建画布窗口
            canvas_window = canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
            
            # 配置画布大小随窗口变化
            def configure_canvas(event):
                canvas.itemconfig(canvas_window, width=event.width)
            
            canvas.bind("<Configure>", configure_canvas)
            
            # 放置画布和滚动条
            canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            
            # 配置画布滚动
            canvas.configure(yscrollcommand=scrollbar.set)
            
            # 配置鼠标滚轮
            def on_mousewheel(event):
                canvas.yview_scroll(int(-1*(event.delta/120)), "units")
            
            # 绑定鼠标滚轮事件
            scrollable_frame.bind("<MouseWheel>", on_mousewheel)
            canvas.bind("<MouseWheel>", on_mousewheel)
            
            return scrollable_frame, container
        
        # 为每个子系统创建标签页
        for subsystem in self.subsystems:
            # 创建标签页
            tab = ttk.Frame(self.notebook)
            self.notebook.add(tab, text=subsystem.name)
            self.tabs[subsystem.name] = tab  # 保存标签页引用
            
            # 创建可滚动框架
            scrollable_frame, _ = create_scrollable_frame(tab)
            
            # 在此标签页中显示该子系统的所有模块和任务
            for module in subsystem.modules:
                module_frame = ttk.LabelFrame(scrollable_frame, text=module.name)
                module_frame.pack(fill=tk.X, padx=5, pady=2, expand=True)
                
                self.task_labels[subsystem.name][module.name] = {}
                
                for task in module.tasks:
                    task_frame = ttk.Frame(module_frame)
                    task_frame.pack(fill=tk.X, padx=20, pady=1)
                    
                    # 移除复选框变量，只使用单选按钮变量
                    effort_ratio_var = tk.StringVar(value="100")  # 默认选择100%
                    self.ui_vars[subsystem.name]['modules'][module.name]['tasks'][task.name] = {
                        'ratio': effort_ratio_var
                    }
                    
                    def make_ratio_callback(s_name, m_name, t_name):
                        def update_effort():
                            # 只有当模块被启用时才更新工作量
                            if self.module_states[s_name].get(m_name, True):
                                # 更新总工作量显示
                                total = self.get_total_effort()
                                self.total_effort_value.configure(text=str(total))
                                
                                # 更新子系统工作量显示
                                subsystem = self.subsystems[self._get_subsystem_index(s_name)]
                                subsystem_effort = subsystem.get_total_effort()
                                self.subsys_effort_labels[s_name].configure(
                                    text=f"(Total Effort: {subsystem_effort})"
                                )
                            
                            # 总是更新模块工作量显示（但如果模块被禁用，会显示为0）
                            module = self.subsystems[self._get_subsystem_index(s_name)].modules[self._get_module_index(s_name, m_name)]
                            module_effort = module.get_total_effort()
                            self.mod_effort_labels[s_name][m_name].configure(
                                text=f"(Effort: {module_effort})"
                            )
                        return update_effort
                    
                    # 任务名称标签
                    ttk.Label(
                        task_frame,
                        text=task.name
                    ).grid(row=0, column=0, sticky='w', padx=(0, 10))
                    
                    # 创建单选按钮框架
                    radio_frame = ttk.Frame(task_frame)
                    radio_frame.grid(row=0, column=1, padx=(0, 10))
                    
                    # 添加四个单选按钮
                    for ratio, text in [("100", "100%"), ("60", "60%"), ("25", "25%"), ("0", "0%")]:
                        ttk.Radiobutton(
                            radio_frame,
                            text=text,
                            variable=effort_ratio_var,
                            value=ratio,
                            command=make_ratio_callback(subsystem.name, module.name, task.name)
                        ).pack(side=tk.LEFT, padx=2)
                    
                    # 工作量标签
                    effort_label = ttk.Label(
                        task_frame,
                        text=f"(Effort: {task.effort})"
                    )
                    effort_label.grid(row=0, column=2, padx=(0, 10))
                    
                    # 分隔符
                    ttk.Label(task_frame, text="-").grid(row=0, column=3, padx=5)
                    
                    # 描述文本
                    description_label = ttk.Label(
                        task_frame,
                        text=task.description,
                        justify=tk.LEFT,
                        wraplength=800
                    )
                    description_label.grid(row=0, column=4, sticky='w', padx=5)
                    
                    # 配置列的宽度和权重
                    task_frame.grid_columnconfigure(0, minsize=150)  # 任务名称列
                    task_frame.grid_columnconfigure(1, minsize=150)  # 单选按钮列
                    task_frame.grid_columnconfigure(2, minsize=100)  # 工作量列
                    task_frame.grid_columnconfigure(3, minsize=20)   # 分隔符列
                    task_frame.grid_columnconfigure(4, weight=1)     # 描述文本列可扩展
                    
                    # 保存工作量标签的引用
                    self.task_labels[subsystem.name][module.name][task.name] = effort_label
                    effort_label.bind('<Double-Button-1>',
                        lambda e, s=subsystem.name, m=module.name, t=task:
                        self.edit_task_effort(s, m, t))
        
        # 设置主窗口的最小大小
        self.root.update()
        min_width = max(800, self.root.winfo_width())
        min_height = max(600, self.root.winfo_height())
        self.root.minsize(min_width, min_height)
        
        # 设置初始窗口大小
        self.root.geometry(f"{min_width}x{min_height}")
        
        # 添加可视化标签页
        self.create_visualization_tab()
    
    def toggle_subsystem(self, subsystem_name, state):
        """当子系统被选中或取消选中时的处理"""
        self.subsystem_states[subsystem_name] = state
        
        # 切换到对应的标签页
        tab_id = self.notebook.tabs().index(str(self.tabs[subsystem_name]))
        self.notebook.select(tab_id)
        
        # 更新UI和内部状态
        for module_name in self.module_states[subsystem_name]:
            # 更新模块状态
            self.module_states[subsystem_name][module_name] = state
            self.ui_vars[subsystem_name]['modules'][module_name]['var'].set(state)
            
            # 更新任务状态
            for task_name in self.ui_vars[subsystem_name]['modules'][module_name]['tasks']:
                self.ui_vars[subsystem_name]['modules'][module_name]['tasks'][task_name]['ratio'].set("100" if state else "0")
        
        # 更新汇总信息
        self.get_summary()

    def toggle_module(self, subsystem_name, module_name, state):
        """当模块被选中或取消选中时的处理"""
        # 切换到对应的标签页
        tab_id = self.notebook.tabs().index(str(self.tabs[subsystem_name]))
        self.notebook.select(tab_id)
        
        # 确保模块状态字典存在
        if subsystem_name not in self.module_states:
            self.module_states[subsystem_name] = {}
        self.module_states[subsystem_name][module_name] = state
        
        # 更新所有任务的单选按钮状态
        for task_name in self.ui_vars[subsystem_name]['modules'][module_name]['tasks']:
            ratio_var = self.ui_vars[subsystem_name]['modules'][module_name]['tasks'][task_name]['ratio']
            ratio_var.set("100" if state else "0")
        
        # 当模块被启用时，确保其所属子系统被启用
        if state:
            self.subsystem_states[subsystem_name] = True
            self.ui_vars[subsystem_name]['var'].set(True)
        # 检查是否需要禁用子系统
        else:
            # 安全地检查所有模块状态
            all_modules_disabled = all(
                not self.module_states.get(subsystem_name, {}).get(mod.name, True)
                for mod in self.subsystems[self._get_subsystem_index(subsystem_name)].modules
            )
            if all_modules_disabled:
                self.subsystem_states[subsystem_name] = False
                self.ui_vars[subsystem_name]['var'].set(False)
        
        # 更新总工作量显示
        self.total_effort_value.configure(text=str(self.get_total_effort()))
        
        # 更新子系统工作量显示
        self.subsys_effort_labels[subsystem_name].configure(
            text=f"(Total Effort: {self.subsystems[self._get_subsystem_index(subsystem_name)].get_total_effort()})"
        )
        
        # 更新模块工作量显示
        module_effort = self.subsystems[self._get_subsystem_index(subsystem_name)].modules[self._get_module_index(subsystem_name, module_name)].get_total_effort()
        self.mod_effort_labels[subsystem_name][module_name].configure(
            text=f"(Effort: {module_effort})"
        )

    def toggle_task(self, subsystem_name, module_name, task_name, state):
        self.task_states[subsystem_name][module_name][task_name] = state
        
        # 当任务被启用时，确保其所属模块和子系统被启用
        if state:
            self.subsystem_states[subsystem_name] = True
            self.module_states[subsystem_name][module_name] = True
            self.ui_vars[subsystem_name]['var'].set(True)
            self.ui_vars[subsystem_name]['modules'][module_name]['var'].set(True)
        # 检查是否需要禁用模块和子系统
        else:
            all_tasks_disabled = all(not self.task_states[subsystem_name][module_name][task.name] 
                                   for task in self.subsystems[self._get_subsystem_index(subsystem_name)]
                                   .modules[self._get_module_index(subsystem_name, module_name)].tasks)
            if all_tasks_disabled:
                self.module_states[subsystem_name][module_name] = False
                self.ui_vars[subsystem_name]['modules'][module_name]['var'].set(False)
                
                # 检查是否需要禁用子系统
                all_modules_disabled = all(not self.module_states[subsystem_name][mod.name] 
                                         for mod in self.subsystems[self._get_subsystem_index(subsystem_name)].modules)
                if all_modules_disabled:
                    self.subsystem_states[subsystem_name] = False
                    self.ui_vars[subsystem_name]['var'].set(False)
        
        # 更新汇总信息
        self.get_summary()

    def _get_subsystem_index(self, subsystem_name):
        """辅助方法：获取子系统索引"""
        for i, subsystem in enumerate(self.subsystems):
            if subsystem.name == subsystem_name:
                return i
        return -1

    def _get_module_index(self, subsystem_name, module_name):
        """辅助方法：获取模块索引"""
        subsystem = self.subsystems[self._get_subsystem_index(subsystem_name)]
        for i, module in enumerate(subsystem.modules):
            if module.name == module_name:
                return i
        return -1

    def add_module_to_subsystem(self, subsystem_name, module):
        """添加模块时初始化其状态"""
        self.module_states[subsystem_name][module.name] = True
        self.task_states[subsystem_name][module.name] = {}
        return module

    def edit_task_effort(self, subsystem_name, module_name, task):
        """编辑任务工作量的对话框"""
        dialog = tk.Toplevel()
        dialog.title(f"Edit Effort - {task.name}")
        dialog.geometry("300x150")
        dialog.transient(dialog.master)
        dialog.grab_set()
        
        # 居中显示
        dialog.geometry("+%d+%d" % (
            dialog.master.winfo_rootx() + dialog.master.winfo_width()/2 - 150,
            dialog.master.winfo_rooty() + dialog.master.winfo_height()/2 - 75
        ))
        
        # 创建输入框和标签
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
                # 更新UI显示
                self.task_labels[subsystem_name][module_name][task.name].configure(
                    text=f"(Effort: {new_effort})"
                )
                # 更新所有相关的工作量显示
                self.update_all_effort_labels(subsystem_name, module_name)
                dialog.destroy()
            except ValueError as e:
                tk.messagebox.showerror("Error", "Please enter a valid number!")
                entry.focus()
        
        def cancel():
            dialog.destroy()
        
        # 创建按钮框架
        button_frame = ttk.Frame(dialog)
        button_frame.pack(pady=20)
        
        ttk.Button(button_frame, text="OK", command=validate_and_save).pack(side=tk.LEFT, padx=10)
        ttk.Button(button_frame, text="Cancel", command=cancel).pack(side=tk.LEFT)
        
        # 绑定回车键到确定按钮
        dialog.bind('<Return>', lambda e: validate_and_save())
        # 绑定Escape键到取消按钮
        dialog.bind('<Escape>', lambda e: cancel())

    def update_all_effort_labels(self, subsystem_name, module_name):
        """更新所有相关的工作量标签"""
        # 更新模块工作量
        module = self.subsystems[self._get_subsystem_index(subsystem_name)].modules[self._get_module_index(subsystem_name, module_name)]
        self.mod_effort_labels[subsystem_name][module_name].configure(
            text=f"(Effort: {module.get_total_effort()})"
        )
        
        # 更新子系统工作量
        subsystem = self.subsystems[self._get_subsystem_index(subsystem_name)]
        self.subsys_effort_labels[subsystem_name].configure(
            text=f"(Total Effort: {subsystem.get_total_effort()})"
        )
        
        # 更新项目总工作量
        self.total_effort_value.configure(text=str(self.get_total_effort()))

    def get_summary(self):
        """更新所有工作量显示"""
        # 更新总工作量
        self.total_effort_value.configure(text=str(self.get_total_effort()))
        
        # 更新每个子系统的工作量
        for subsystem in self.subsystems:
            self.subsys_effort_labels[subsystem.name].configure(
                text=f"(Total Effort: {subsystem.get_total_effort()})"
            )
            # 更新该子系统下每个模块的工作量
            for module in subsystem.modules:
                self.mod_effort_labels[subsystem.name][module.name].configure(
                    text=f"(Effort: {module.get_total_effort()})"
                )

    def create_visualization_tab(self):
        """创建可视化标签页"""
        import matplotlib.pyplot as plt
        from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
        from matplotlib.figure import Figure
        import tkinter as tk
        from tkinter import ttk  # 添加这行导入
        
        # 创建可视化标签页
        viz_tab = ttk.Frame(self.notebook)
        self.notebook.add(viz_tab, text="Visualization")
        
        # 创建左右分栏
        left_frame = ttk.Frame(viz_tab)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        right_frame = ttk.Frame(viz_tab)
        right_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 创建图表
        def create_subsystem_pie():
            # 收集数据
            labels = []
            sizes = []
            for subsystem in self.subsystems:
                if self.subsystem_states.get(subsystem.name, True):
                    effort = subsystem.get_total_effort()
                    if effort > 0:  # 只显示非零工作量
                        labels.append(subsystem.name)
                        sizes.append(effort)
            
            # 创建饼图
            fig = Figure(figsize=(6, 4))
            ax = fig.add_subplot(111)
            ax.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=90)
            ax.axis('equal')
            ax.set_title('Subsystem Effort Distribution')
            
            return fig
        
        def create_module_bar():
            # 收集数据
            modules = []
            efforts = []
            colors = []
            
            for subsystem in self.subsystems:
                if self.subsystem_states.get(subsystem.name, True):
                    for module in subsystem.modules:
                        if self.module_states[subsystem.name].get(module.name, True):
                            effort = module.get_total_effort()
                            if effort > 0:  # 只显示非零工作量
                                modules.append(f"{subsystem.name}\n{module.name}")
                                efforts.append(effort)
                                colors.append(plt.cm.Set3(len(modules) % 12))
            
            # 创建柱状图
            fig = Figure(figsize=(6, 4))
            ax = fig.add_subplot(111)
            bars = ax.bar(range(len(modules)), efforts, color=colors)
            ax.set_xticks(range(len(modules)))
            ax.set_xticklabels(modules, rotation=45, ha='right')
            ax.set_title('Module Effort Comparison')
            ax.set_ylabel('Effort')
            
            # 添加数值标签
            for bar in bars:
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2., height,
                       f'{int(height)}',
                       ha='center', va='bottom')
            
            fig.tight_layout()
            return fig
        
        # 创建图表显示区域
        pie_canvas = FigureCanvasTkAgg(create_subsystem_pie(), left_frame)
        pie_canvas.draw()
        pie_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        bar_canvas = FigureCanvasTkAgg(create_module_bar(), right_frame)
        bar_canvas.draw()
        bar_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        # 添加刷新按钮
        def refresh_charts():
            # 清除旧图表
            for widget in left_frame.winfo_children():
                widget.destroy()
            for widget in right_frame.winfo_children():
                widget.destroy()
            
            # 创建新图表
            pie_canvas = FigureCanvasTkAgg(create_subsystem_pie(), left_frame)
            pie_canvas.draw()
            pie_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
            
            bar_canvas = FigureCanvasTkAgg(create_module_bar(), right_frame)
            bar_canvas.draw()
            bar_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
            
            # 确保刷新按钮只添加一次
            if not refresh_button.winfo_ismapped():
                refresh_button.pack(pady=5)
        
        ttk.Button(viz_tab, text="Refresh Charts", command=refresh_charts).pack(pady=5)

# 修改主程序入口
if __name__ == "__main__":
    # 使用CSV文件初始化估算器
    estimator = EffortEstimator("effort_data.csv")
    # 启动UI界面
    estimator.create_ui()
    # 在这里调用 mainloop
    estimator.root.mainloop()
