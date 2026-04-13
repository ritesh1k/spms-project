import tkinter as tk
from datetime import datetime
from tkinter import ttk, messagebox

from db_config import get_connection
from modules.course_aliases import canonical_course_name, get_course_aliases
from modules.result_utils import normalize_semester


SEMESTER_VALUES = [str(value) for value in range(1, 9)]
SECTION_VALUES = ["A", "B", "C", "D", "E", "F"]
LECTURE_DAY_VALUES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]


def ensure_assigned_subject_table():
	conn = get_connection()
	cursor = conn.cursor()
	cursor.execute(
		"""
		CREATE TABLE IF NOT EXISTS assigned_subjects (
			assigned_id INT AUTO_INCREMENT PRIMARY KEY,
			department_id INT NOT NULL,
			department_name VARCHAR(120) NOT NULL,
			course_id INT NOT NULL,
			course_name VARCHAR(150) NOT NULL,
			teacher_username VARCHAR(100) DEFAULT NULL,
			teacher_name VARCHAR(150) NOT NULL,
			teacher_email VARCHAR(150) NOT NULL,
			semester VARCHAR(10) NOT NULL,
			section VARCHAR(10) NOT NULL,
			subject_id INT NOT NULL,
			subject_name VARCHAR(150) NOT NULL,
			subject_code VARCHAR(50) NOT NULL,
			lecture_day VARCHAR(20) NOT NULL,
			lecture_time VARCHAR(20) NOT NULL,
			room_number VARCHAR(50) NOT NULL,
			created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
			updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
			INDEX idx_assigned_department (department_id),
			INDEX idx_assigned_course (course_id),
			INDEX idx_assigned_teacher (teacher_email),
			INDEX idx_assigned_subject (subject_id)
		)
		"""
	)
	conn.commit()
	conn.close()


def load_module(parent_frame, update_stats_callback=None):
	"""Load Assign Subject module into parent frame."""
	for widget in parent_frame.winfo_children():
		widget.destroy()

	try:
		ensure_assigned_subject_table()
	except Exception as exc:
		messagebox.showerror("Database Error", f"Failed to prepare assigned subjects table: {exc}")

	title_frame = tk.Frame(parent_frame, bg="#8e44ad", height=60)
	title_frame.pack(fill="x")
	title_frame.pack_propagate(False)

	tk.Label(
		title_frame,
		text="📚 Assign Subjects",
		font=("Segoe UI", 18, "bold"),
		bg="#8e44ad",
		fg="white",
	).pack(side="left", pady=15, padx=20)

	content_frame = tk.Frame(parent_frame, bg="#f5f7fa")
	content_frame.pack(fill="both", expand=True, padx=20, pady=20)

	form_card = tk.Frame(content_frame, bg="white", bd=1, relief="solid")
	form_card.pack(fill="x", pady=(0, 18))

	tk.Label(
		form_card,
		text="Assignment Details",
		font=("Segoe UI", 14, "bold"),
		bg="white",
		fg="#2c3e50",
	).pack(anchor="w", padx=24, pady=(18, 0))

	tk.Label(
		form_card,
		text="Select the department, course, teacher, subject, schedule and room before saving.",
		font=("Segoe UI", 9),
		bg="white",
		fg="#7f8c8d",
	).pack(anchor="w", padx=24, pady=(4, 8))

	department_var = tk.StringVar(value="Select Department")
	course_var = tk.StringVar(value="Select Course")
	teacher_var = tk.StringVar(value="Select Teacher")
	teacher_email_var = tk.StringVar(value="")
	semester_var = tk.StringVar(value="Select Semester")
	section_var = tk.StringVar(value="Select Section")
	subject_var = tk.StringVar(value="Select Subject")
	subject_code_var = tk.StringVar(value="")
	lecture_day_var = tk.StringVar(value="Select Day")
	lecture_time_var = tk.StringVar(value="")
	room_number_var = tk.StringVar(value="")
	assigned_count_var = tk.StringVar(value="Unique Subjects: 0")
	edit_state_var = tk.StringVar(value="Mode: New Assignment")

	tk.Label(
		form_card,
		textvariable=edit_state_var,
		font=("Segoe UI", 9, "bold"),
		bg="white",
		fg="#8e44ad",
	).pack(anchor="w", padx=24, pady=(0, 8))

	form_grid = tk.Frame(form_card, bg="white")
	form_grid.pack(fill="x", padx=24, pady=(0, 18))

	department_map = {}
	course_map = {}
	teacher_map = {}
	subject_map = {}
	current_assignment_id = {"value": None}

	def get_department_rows():
		conn = get_connection()
		cursor = conn.cursor()
		cursor.execute(
			"SELECT department_id, department_name FROM departments WHERE is_active = 1 ORDER BY department_name"
		)
		rows = cursor.fetchall()
		cursor.close()
		conn.close()
		return rows

	def build_course_values(rows):
		values = []
		mapping = {}
		for course_id, course_name in rows:
			display_name = canonical_course_name(course_name)
			if display_name not in values:
				values.append(display_name)
			mapping[display_name] = course_id
		return values, mapping

	def set_dropdown_values(dropdown, values, default_value):
		dropdown["values"] = values
		dropdown.set(default_value)

	def create_label(text, row, column):
		tk.Label(
			form_grid,
			text=text,
			font=("Segoe UI", 10, "bold"),
			bg="white",
			fg="#2c3e50",
			anchor="w",
		).grid(row=row, column=column, sticky="w", padx=(0, 12), pady=10)

	def create_combo(variable, row, column, values, width=17):
		combo = ttk.Combobox(
			form_grid,
			textvariable=variable,
			values=values,
			state="readonly",
			font=("Segoe UI", 10),
			width=width,
		)
		combo.grid(row=row, column=column, sticky="w", padx=(0, 24), pady=10)
		return combo

	def create_entry(variable, row, column, width=18, state="normal"):
		entry = tk.Entry(
			form_grid,
			textvariable=variable,
			font=("Segoe UI", 10),
			relief="solid",
			bd=1,
			width=width,
			state=state,
		)
		entry.grid(row=row, column=column, sticky="w", padx=(0, 24), pady=10)
		return entry

	create_label("Department:", 0, 0)
	department_dropdown = create_combo(department_var, 0, 1, ["Select Department"])
	create_label("Course:", 0, 2)
	course_dropdown = create_combo(course_var, 0, 3, ["Select Course"])

	create_label("Teacher Name:", 1, 0)
	teacher_dropdown = create_combo(teacher_var, 1, 1, ["Select Teacher"])
	create_label("Teacher Email:", 1, 2)
	create_entry(teacher_email_var, 1, 3, state="readonly")

	create_label("Semester:", 2, 0)
	semester_dropdown = create_combo(semester_var, 2, 1, ["Select Semester"] + SEMESTER_VALUES)
	create_label("Section:", 2, 2)
	create_combo(section_var, 2, 3, ["Select Section"] + SECTION_VALUES)

	create_label("Subject Name:", 3, 0)
	subject_dropdown = create_combo(subject_var, 3, 1, ["Select Subject"])
	create_label("Subject Code:", 3, 2)
	create_entry(subject_code_var, 3, 3, state="readonly")

	create_label("Lecture Day:", 4, 0)
	create_combo(lecture_day_var, 4, 1, ["Select Day"] + LECTURE_DAY_VALUES)
	create_label("Lecture Time:", 4, 2)
	create_entry(lecture_time_var, 4, 3)

	create_label("Room Number:", 5, 0)
	create_entry(room_number_var, 5, 1)
	tk.Label(
		form_grid,
		text="Use 24-hour range format for lecture time, for example 09:30 to 10:30.",
		font=("Segoe UI", 9),
		bg="white",
		fg="#7f8c8d",
	).grid(row=5, column=2, columnspan=2, sticky="w", pady=10)

	for column in [1, 3]:
		form_grid.columnconfigure(column, weight=0)

	departments = []
	try:
		departments = get_department_rows()
	except Exception as exc:
		messagebox.showerror("Error", f"Failed to load departments: {exc}")

	department_map = {department_name: department_id for department_id, department_name in departments}
	set_dropdown_values(
		department_dropdown,
		["Select Department"] + [department_name for _, department_name in departments],
		"Select Department",
	)

	def reset_teacher_selection():
		nonlocal teacher_map
		teacher_map = {}
		set_dropdown_values(teacher_dropdown, ["Select Teacher"], "Select Teacher")
		teacher_email_var.set("")

	def reset_subject_selection():
		nonlocal subject_map
		subject_map = {}
		set_dropdown_values(subject_dropdown, ["Select Subject"], "Select Subject")
		subject_code_var.set("")

	def load_courses_for_department(_event=None):
		nonlocal course_map
		course_map = {}
		reset_teacher_selection()
		reset_subject_selection()
		dept_name = department_var.get().strip()
		if dept_name == "Select Department":
			set_dropdown_values(course_dropdown, ["Select Course"], "Select Course")
			return

		try:
			conn = get_connection()
			cursor = conn.cursor()
			cursor.execute(
				"""
				SELECT course_id, course_name
				FROM courses
				WHERE department_id = %s AND is_active = 1
				ORDER BY course_name
				""",
				(department_map.get(dept_name),),
			)
			rows = cursor.fetchall()
			cursor.close()
			conn.close()

			course_values, course_map = build_course_values(rows)
			set_dropdown_values(course_dropdown, ["Select Course"] + course_values, "Select Course")
		except Exception as exc:
			messagebox.showerror("Error", f"Failed to load courses: {exc}")
			set_dropdown_values(course_dropdown, ["Select Course"], "Select Course")

	def load_teachers_for_selection(_event=None):
		nonlocal teacher_map
		teacher_map = {}
		reset_subject_selection()
		teacher_email_var.set("")

		dept_name = department_var.get().strip()
		course_name = course_var.get().strip()
		if dept_name == "Select Department" or course_name == "Select Course":
			reset_teacher_selection()
			return

		try:
			conn = get_connection()
			cursor = conn.cursor()
			course_aliases = get_course_aliases(course_name)
			placeholders = ",".join(["%s"] * len(course_aliases))
			query = f"""
				SELECT username,
					   COALESCE(NULLIF(full_name, ''), username) AS teacher_name,
					   email
				FROM teachers
				WHERE role='teacher' AND department=%s
				  AND (COALESCE(course, '') IN ({placeholders}) OR COALESCE(specialization, '') IN ({placeholders}))
				ORDER BY teacher_name, email
			"""
			params = [dept_name] + course_aliases + course_aliases
			cursor.execute(query, tuple(params))
			rows = cursor.fetchall()
			cursor.close()
			conn.close()

			teacher_values = []
			for username, teacher_name, email in rows:
				display_name = teacher_name
				if display_name in teacher_map:
					display_name = f"{teacher_name} ({email})"
				teacher_values.append(display_name)
				teacher_map[display_name] = {
					"username": username,
					"name": teacher_name,
					"email": email,
				}

			set_dropdown_values(teacher_dropdown, ["Select Teacher"] + teacher_values, "Select Teacher")
		except Exception as exc:
			messagebox.showerror("Error", f"Failed to load teachers: {exc}")
			reset_teacher_selection()

	def load_subjects_for_selection(_event=None):
		nonlocal subject_map
		subject_map = {}
		subject_code_var.set("")

		dept_name = department_var.get().strip()
		course_name = course_var.get().strip()
		semester_text = semester_var.get().strip()
		if dept_name == "Select Department" or course_name == "Select Course" or semester_text == "Select Semester":
			reset_subject_selection()
			return

		semester_values = [semester_text, normalize_semester(semester_text)]
		semester_values = [v for i, v in enumerate(semester_values) if v and v not in semester_values[:i]]

		try:
			conn = get_connection()
			cursor = conn.cursor()
			placeholders = ",".join(["%s"] * len(semester_values))
			query = f"""
				SELECT subject_id, subject_name, subject_code
				FROM subjects
				WHERE department_id = %s
				  AND course_id = %s
				  AND is_active = 1
				  AND semester IN ({placeholders})
				ORDER BY subject_name
			"""
			params = [department_map.get(dept_name), course_map.get(course_name)] + semester_values
			cursor.execute(query, tuple(params))
			rows = cursor.fetchall()
			cursor.close()
			conn.close()

			subject_values = []
			for subject_id, subject_name, subject_code in rows:
				if subject_name not in subject_values:
					subject_values.append(subject_name)
				if subject_name not in subject_map:
					subject_map[subject_name] = {"id": subject_id, "code": subject_code}

			set_dropdown_values(subject_dropdown, ["Select Subject"] + subject_values, "Select Subject")
		except Exception as exc:
			messagebox.showerror("Error", f"Failed to load subjects: {exc}")
			reset_subject_selection()

	def on_teacher_change(_event=None):
		selected_teacher = teacher_map.get(teacher_var.get().strip())
		teacher_email_var.set(selected_teacher["email"] if selected_teacher else "")

	def on_subject_change(_event=None):
		selected_subject = subject_map.get(subject_var.get().strip())
		subject_code_var.set(selected_subject["code"] if selected_subject else "")

	def clear_form():
		department_var.set("Select Department")
		set_dropdown_values(course_dropdown, ["Select Course"], "Select Course")
		reset_teacher_selection()
		semester_var.set("Select Semester")
		section_var.set("Select Section")
		reset_subject_selection()
		lecture_day_var.set("Select Day")
		lecture_time_var.set("")
		room_number_var.set("")
		current_assignment_id["value"] = None
		edit_state_var.set("Mode: New Assignment")

	def validate_time(value):
		try:
			parts = [part.strip() for part in str(value).split(" to ")]
			if len(parts) != 2:
				return None
			start_time = datetime.strptime(parts[0], "%H:%M")
			end_time = datetime.strptime(parts[1], "%H:%M")
			if end_time <= start_time:
				return None
			return f"{start_time.strftime('%H:%M')} to {end_time.strftime('%H:%M')}"
		except ValueError:
			return None

	def refresh_assigned_subjects():
		for item in assignment_tree.get_children():
			assignment_tree.delete(item)

		try:
			conn = get_connection()
			cursor = conn.cursor()
			cursor.execute(
				"""
				SELECT assigned_id, department_name, course_name, teacher_name, teacher_email,
					   semester, section, subject_name, subject_code, lecture_day,
					   lecture_time, room_number
				FROM assigned_subjects
				ORDER BY assigned_id ASC
				"""
			)
			rows = cursor.fetchall()
			cursor.close()
			conn.close()

			unique_subject_codes = set()
			for row in rows:
				assignment_tree.insert("", "end", values=row)
				unique_subject_codes.add(str(row[8]).strip())

			assigned_count_var.set(f"Unique Subjects: {len(unique_subject_codes)}")
		except Exception as exc:
			messagebox.showerror("Error", f"Failed to load assigned subjects: {exc}")

	def collect_form_data():
		dept_name = department_var.get().strip()
		course_name = course_var.get().strip()
		teacher_name_display = teacher_var.get().strip()
		semester_text = semester_var.get().strip()
		section_text = section_var.get().strip()
		subject_name = subject_var.get().strip()
		lecture_day = lecture_day_var.get().strip()
		lecture_time = validate_time(lecture_time_var.get().strip())
		room_number = room_number_var.get().strip()

		if dept_name == "Select Department":
			messagebox.showerror("Error", "Please select a department")
			return None
		if course_name == "Select Course":
			messagebox.showerror("Error", "Please select a course")
			return None
		if teacher_name_display == "Select Teacher" or teacher_name_display not in teacher_map:
			messagebox.showerror("Error", "Please select a teacher")
			return None
		if semester_text == "Select Semester":
			messagebox.showerror("Error", "Please select a semester")
			return None
		if section_text == "Select Section":
			messagebox.showerror("Error", "Please select a section")
			return None
		if subject_name == "Select Subject" or subject_name not in subject_map:
			messagebox.showerror("Error", "Please select a subject")
			return None
		if lecture_day == "Select Day":
			messagebox.showerror("Error", "Please select a lecture day")
			return None
		if not lecture_time:
			messagebox.showerror("Error", "Lecture time must be in HH:MM to HH:MM format")
			return None
		if not room_number:
			messagebox.showerror("Error", "Please enter a room number")
			return None

		teacher_data = teacher_map[teacher_name_display]
		subject_data = subject_map[subject_name]
		return {
			"department_id": department_map[dept_name],
			"department_name": dept_name,
			"course_id": course_map[course_name],
			"course_name": course_name,
			"teacher_username": teacher_data["username"],
			"teacher_name": teacher_data["name"],
			"teacher_email": teacher_data["email"],
			"semester": semester_text,
			"section": section_text,
			"subject_id": subject_data["id"],
			"subject_name": subject_name,
			"subject_code": subject_data["code"],
			"lecture_day": lecture_day,
			"lecture_time": lecture_time,
			"room_number": room_number,
		}

	def find_teacher_display(email_value, fallback_name):
		for display_name, data in teacher_map.items():
			if data["email"] == email_value:
				return display_name
		return fallback_name

	def load_selected_assignment(assignment_id):
		try:
			conn = get_connection()
			cursor = conn.cursor()
			cursor.execute(
				"""
				SELECT assigned_id, department_name, course_name, teacher_name, teacher_email,
					   semester, section, subject_name, lecture_day, lecture_time, room_number
				FROM assigned_subjects
				WHERE assigned_id=%s
				LIMIT 1
				""",
				(assignment_id,),
			)
			row = cursor.fetchone()
			cursor.close()
			conn.close()
			if not row:
				messagebox.showerror("Error", "Selected assignment not found.")
				return

			department_var.set(row[1])
			load_courses_for_department()
			course_var.set(row[2])
			load_teachers_for_selection()
			teacher_var.set(find_teacher_display(row[4], row[3]))
			on_teacher_change()
			semester_var.set(str(row[5]))
			section_var.set(str(row[6]))
			load_subjects_for_selection()
			subject_var.set(row[7])
			on_subject_change()
			lecture_day_var.set(row[8])
			lecture_time_var.set(str(row[9]))
			room_number_var.set(str(row[10]))
			current_assignment_id["value"] = int(row[0])
			edit_state_var.set(f"Mode: Editing Assigned ID {row[0]}")
		except Exception as exc:
			messagebox.showerror("Error", f"Failed to load selected assignment: {exc}")

	def assign_subject():
		form_data = collect_form_data()
		if not form_data:
			return

		try:
			conn = get_connection()
			cursor = conn.cursor()
			cursor.execute(
				"""
				SELECT assigned_id
				FROM assigned_subjects
				WHERE department_id=%s AND course_id=%s AND teacher_email=%s
				  AND semester=%s AND section=%s AND subject_id=%s
				  AND lecture_day=%s AND lecture_time=%s AND room_number=%s
				LIMIT 1
				""",
				(
					form_data["department_id"],
					form_data["course_id"],
					form_data["teacher_email"],
					form_data["semester"],
					form_data["section"],
					form_data["subject_id"],
					form_data["lecture_day"],
					form_data["lecture_time"],
					form_data["room_number"],
				),
			)
			if cursor.fetchone():
				cursor.close()
				conn.close()
				messagebox.showwarning("Duplicate", "This subject assignment already exists.")
				return

			cursor.execute(
				"""
				INSERT INTO assigned_subjects (
					department_id, department_name, course_id, course_name,
					teacher_username, teacher_name, teacher_email, semester,
					section, subject_id, subject_name, subject_code,
					lecture_day, lecture_time, room_number
				)
				VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
				""",
				(
					form_data["department_id"],
					form_data["department_name"],
					form_data["course_id"],
					form_data["course_name"],
					form_data["teacher_username"],
					form_data["teacher_name"],
					form_data["teacher_email"],
					form_data["semester"],
					form_data["section"],
					form_data["subject_id"],
					form_data["subject_name"],
					form_data["subject_code"],
					form_data["lecture_day"],
					form_data["lecture_time"],
					form_data["room_number"],
				),
			)
			conn.commit()
			cursor.close()
			conn.close()

			messagebox.showinfo("Success", "Subject assigned successfully.")
			refresh_assigned_subjects()
			clear_form()
			if callable(update_stats_callback):
				update_stats_callback()
		except Exception as exc:
			messagebox.showerror("Error", f"Failed to assign subject: {exc}")

	def update_assignment():
		assignment_id = current_assignment_id["value"]
		if not assignment_id:
			messagebox.showwarning("Select Record", "Select an assigned subject from the table to edit.")
			return

		form_data = collect_form_data()
		if not form_data:
			return

		try:
			conn = get_connection()
			cursor = conn.cursor()
			cursor.execute(
				"""
				SELECT assigned_id
				FROM assigned_subjects
				WHERE department_id=%s AND course_id=%s AND teacher_email=%s
				  AND semester=%s AND section=%s AND subject_id=%s
				  AND lecture_day=%s AND lecture_time=%s AND room_number=%s
				  AND assigned_id<>%s
				LIMIT 1
				""",
				(
					form_data["department_id"],
					form_data["course_id"],
					form_data["teacher_email"],
					form_data["semester"],
					form_data["section"],
					form_data["subject_id"],
					form_data["lecture_day"],
					form_data["lecture_time"],
					form_data["room_number"],
					assignment_id,
				),
			)
			if cursor.fetchone():
				cursor.close()
				conn.close()
				messagebox.showwarning("Duplicate", "Another assignment already exists with the same details.")
				return

			cursor.execute(
				"""
				UPDATE assigned_subjects
				SET department_id=%s,
					department_name=%s,
					course_id=%s,
					course_name=%s,
					teacher_username=%s,
					teacher_name=%s,
					teacher_email=%s,
					semester=%s,
					section=%s,
					subject_id=%s,
					subject_name=%s,
					subject_code=%s,
					lecture_day=%s,
					lecture_time=%s,
					room_number=%s
				WHERE assigned_id=%s
				""",
				(
					form_data["department_id"],
					form_data["department_name"],
					form_data["course_id"],
					form_data["course_name"],
					form_data["teacher_username"],
					form_data["teacher_name"],
					form_data["teacher_email"],
					form_data["semester"],
					form_data["section"],
					form_data["subject_id"],
					form_data["subject_name"],
					form_data["subject_code"],
					form_data["lecture_day"],
					form_data["lecture_time"],
					form_data["room_number"],
					assignment_id,
				),
			)
			conn.commit()
			cursor.close()
			conn.close()

			messagebox.showinfo("Success", "Assigned subject updated successfully.")
			refresh_assigned_subjects()
			clear_form()
		except Exception as exc:
			messagebox.showerror("Error", f"Failed to update assigned subject: {exc}")

	button_row = tk.Frame(form_card, bg="white")
	button_row.pack(fill="x", padx=24, pady=(0, 20))

	tk.Button(
		button_row,
		text="Assign Subject",
		command=assign_subject,
		bg="#8e44ad",
		fg="white",
		relief="flat",
		cursor="hand2",
		font=("Segoe UI", 10, "bold"),
		padx=18,
		pady=8,
	).pack(side="left", padx=(0, 10))

	tk.Button(
		button_row,
		text="Update Selected",
		command=update_assignment,
		bg="#16a085",
		fg="white",
		relief="flat",
		cursor="hand2",
		font=("Segoe UI", 10, "bold"),
		padx=18,
		pady=8,
	).pack(side="left", padx=(0, 10))

	tk.Button(
		button_row,
		text="Clear Form",
		command=clear_form,
		bg="#95a5a6",
		fg="white",
		relief="flat",
		cursor="hand2",
		font=("Segoe UI", 10),
		padx=18,
		pady=8,
	).pack(side="left", padx=(0, 10))

	tk.Button(
		button_row,
		text="View Assigned Subjects",
		command=refresh_assigned_subjects,
		bg="#3498db",
		fg="white",
		relief="flat",
		cursor="hand2",
		font=("Segoe UI", 10),
		padx=18,
		pady=8,
	).pack(side="left")

	list_card = tk.Frame(content_frame, bg="white", bd=1, relief="solid")
	list_card.pack(fill="both", expand=True)

	header_row = tk.Frame(list_card, bg="white")
	header_row.pack(fill="x", padx=18, pady=(16, 6))

	tk.Label(
		header_row,
		text="Assigned Subjects List",
		font=("Segoe UI", 13, "bold"),
		bg="white",
		fg="#2c3e50",
	).pack(side="left")

	tk.Label(
		header_row,
		textvariable=assigned_count_var,
		font=("Segoe UI", 10),
		bg="white",
		fg="#7f8c8d",
	).pack(side="right")

	tree_wrapper = tk.Frame(list_card, bg="white")
	tree_wrapper.pack(fill="both", expand=True, padx=18, pady=(0, 18))

	tree_scroll_y = ttk.Scrollbar(tree_wrapper, orient="vertical")
	tree_scroll_x = ttk.Scrollbar(tree_wrapper, orient="horizontal")

	columns = (
		"ID", "Department", "Course", "Teacher", "Email", "Semester",
		"Section", "Subject", "Code", "Day", "Time", "Room"
	)
	assignment_tree = ttk.Treeview(
		tree_wrapper,
		columns=columns,
		show="headings",
		yscrollcommand=tree_scroll_y.set,
		xscrollcommand=tree_scroll_x.set,
		height=12,
	)

	tree_scroll_y.config(command=assignment_tree.yview)
	tree_scroll_x.config(command=assignment_tree.xview)
	tree_scroll_y.pack(side="right", fill="y")
	tree_scroll_x.pack(side="bottom", fill="x")
	assignment_tree.pack(fill="both", expand=True)

	column_widths = {
		"ID": 60,
		"Department": 160,
		"Course": 140,
		"Teacher": 170,
		"Email": 220,
		"Semester": 80,
		"Section": 80,
		"Subject": 200,
		"Code": 110,
		"Day": 110,
		"Time": 130,
		"Room": 110,
	}

	for column in columns:
		anchor = "center" if column in {"ID", "Semester", "Section", "Time"} else "w"
		assignment_tree.heading(column, text=column)
		assignment_tree.column(column, width=column_widths[column], anchor=anchor)

	def on_assignment_select(_event=None):
		selected = assignment_tree.focus()
		if not selected:
			return
		values = assignment_tree.item(selected, "values")
		if not values:
			return
		load_selected_assignment(values[0])

	department_dropdown.bind("<<ComboboxSelected>>", load_courses_for_department)
	course_dropdown.bind("<<ComboboxSelected>>", load_teachers_for_selection)
	course_dropdown.bind("<<ComboboxSelected>>", load_subjects_for_selection, add="+")
	semester_dropdown.bind("<<ComboboxSelected>>", load_subjects_for_selection)
	teacher_dropdown.bind("<<ComboboxSelected>>", on_teacher_change)
	subject_dropdown.bind("<<ComboboxSelected>>", on_subject_change)
	assignment_tree.bind("<<TreeviewSelect>>", on_assignment_select)

	refresh_assigned_subjects()