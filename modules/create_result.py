import importlib
import tkinter as tk
from datetime import datetime
from tkinter import ttk, messagebox, filedialog

from db_config import get_connection
from modules.result_utils import ensure_result_tables


def load_module(parent_frame, teacher_username=None, update_stats_callback=None):
	for widget in parent_frame.winfo_children():
		widget.destroy()
	parent_frame.configure(bg="#f5f7fa")

	ensure_result_tables(include_published=False)

	title_frame = tk.Frame(parent_frame, bg="#9b59b6", height=60)
	title_frame.pack(fill="x")
	title_frame.pack_propagate(False)

	tk.Label(
		title_frame,
		text="🧾 Internal Result Entry (Teacher)",
		font=("Segoe UI", 16, "bold"),
		bg="#9b59b6",
		fg="white",
	).pack(pady=12)

	content = tk.Frame(parent_frame, bg="#f5f7fa")
	content.pack(fill="both", expand=True, padx=16, pady=16)

	form = tk.Frame(content, bg="white", bd=1, relief="solid")
	form.pack(fill="x", padx=4, pady=(0, 10))

	fields_frame = tk.Frame(form, bg="white")
	fields_frame.pack(fill="x", padx=16, pady=14)

	filter_frame = tk.Frame(form, bg="white")
	filter_frame.pack(fill="x", padx=16, pady=(14, 0))

	enrollment_var = tk.StringVar()
	student_name_var = tk.StringVar(value="")
	subject_var = tk.StringVar()
	semester_var = tk.StringVar(value="I")
	assignment_var = tk.StringVar(value="0")
	attendance_var = tk.StringVar(value="0")
	ct1_var = tk.StringVar(value="0")
	ct2_var = tk.StringVar(value="0")
	ct3_var = tk.StringVar(value="0")
	dept_filter_var = tk.StringVar(value="All")
	course_filter_var = tk.StringVar(value="All")
	sem_filter_var = tk.StringVar(value="All")
	section_filter_var = tk.StringVar(value="All")

	def get_teacher_department():
		if not teacher_username:
			return None
		try:
			conn = get_connection()
			cur = conn.cursor()
			cur.execute("SELECT department FROM teachers WHERE username=%s LIMIT 1", (teacher_username,))
			row = cur.fetchone()
			conn.close()
			if row and row[0]:
				return str(row[0]).strip()
		except Exception:
			pass
		return None

	teacher_department = get_teacher_department()

	ct_best_label = tk.Label(fields_frame, text="CT Best Two: 0 / 20", font=("Segoe UI", 10, "bold"), bg="white", fg="#2c3e50")
	total_label = tk.Label(fields_frame, text="Internal Total: 0 / 40", font=("Segoe UI", 11, "bold"), bg="white", fg="#16a085")

	def get_students(course_filter="All", semester_filter="All", section_filter="All"):
		try:
			conn = get_connection()
			cur = conn.cursor()
			where = []
			params = []
			if teacher_department:
				where.append("department=%s")
				params.append(teacher_department)
			if course_filter != "All":
				where.append("course=%s")
				params.append(course_filter)
			if semester_filter != "All":
				where.append("semester=%s")
				params.append(semester_filter)
			if section_filter != "All":
				where.append("section=%s")
				params.append(section_filter)

			query = "SELECT enrollment_no, name, semester, course, section FROM students"
			if where:
				query += " WHERE " + " AND ".join(where)
			query += " ORDER BY enrollment_no"
			cur.execute(query, tuple(params))
			rows = cur.fetchall()
			conn.close()
			return rows
		except Exception:
			return []

	students = get_students()
	student_map = {row[0]: (row[1], row[2]) for row in students}

	def get_distinct_values(column, course_filter="All", semester_filter="All"):
		try:
			conn = get_connection()
			cur = conn.cursor()
			where = []
			params = []
			if teacher_department:
				where.append("department=%s")
				params.append(teacher_department)
			if course_filter != "All":
				where.append("course=%s")
				params.append(course_filter)
			if semester_filter != "All":
				where.append("semester=%s")
				params.append(semester_filter)
			query = f"SELECT DISTINCT {column} FROM students"
			if where:
				query += " WHERE " + " AND ".join(where)
			query += f" ORDER BY {column}"
			cur.execute(query, tuple(params))
			rows = [str(row[0]).strip() for row in cur.fetchall() if str(row[0]).strip()]
			conn.close()
			return rows
		except Exception:
			return []

	tk.Label(filter_frame, text="Department", bg="white", font=("Segoe UI", 10, "bold")).pack(side="left", padx=(0, 8), pady=6)
	dept_values = [teacher_department] if teacher_department else ["All"]
	dept_filter_var.set(dept_values[0])
	dept_combo = ttk.Combobox(filter_frame, textvariable=dept_filter_var, state="readonly", values=dept_values, width=16)
	dept_combo.pack(side="left", padx=(0, 18), pady=6)

	tk.Label(filter_frame, text="Course", background="white", font=("Segoe UI", 10, "bold")).pack(side="left", padx=(0, 8), pady=6)
	course_combo_filter = ttk.Combobox(filter_frame, textvariable=course_filter_var, state="readonly", values=["All"], width=14)
	course_combo_filter.pack(side="left", padx=(0, 18), pady=6)

	tk.Label(filter_frame, text="Semester", background="white", font=("Segoe UI", 10, "bold")).pack(side="left", padx=(0, 8), pady=6)
	sem_combo_filter = ttk.Combobox(filter_frame, textvariable=sem_filter_var, state="readonly", values=["All"], width=10)
	sem_combo_filter.pack(side="left", padx=(0, 18), pady=6)

	tk.Label(filter_frame, text="Section", background="white", font=("Segoe UI", 10, "bold")).pack(side="left", padx=(0, 8), pady=6)
	section_combo_filter = ttk.Combobox(filter_frame, textvariable=section_filter_var, state="readonly", values=["All"], width=10)
	section_combo_filter.pack(side="left", padx=(0, 8), pady=6)

	tk.Label(fields_frame, text="Enrollment", bg="white", font=("Segoe UI", 10)).grid(row=0, column=0, sticky="w", padx=(0, 8), pady=6)
	enrollment_combo = ttk.Combobox(fields_frame, textvariable=enrollment_var, state="readonly", values=[r[0] for r in students], width=26)
	enrollment_combo.grid(row=0, column=1, sticky="w", padx=(0, 18), pady=6)

	tk.Label(fields_frame, text="Student Name", bg="white", font=("Segoe UI", 10)).grid(row=0, column=2, sticky="w", padx=(0, 8), pady=6)
	tk.Label(fields_frame, textvariable=student_name_var, bg="white", fg="#334155", font=("Segoe UI", 10, "bold"), width=25, anchor="w").grid(row=0, column=3, sticky="w", pady=6)

	def get_teacher_assigned_subjects():
		if not teacher_username:
			return []
		try:
			conn = get_connection()
			cur = conn.cursor()
			cur.execute("""
				SELECT DISTINCT subject_name 
				FROM assigned_subjects 
				WHERE teacher_username=%s AND subject_name IS NOT NULL
				ORDER BY subject_name
			""", (teacher_username,))
			rows = [str(row[0]).strip() for row in cur.fetchall() if str(row[0]).strip()]
			conn.close()
			return rows
		except Exception:
			return []

	assigned_subjects = get_teacher_assigned_subjects()

	tk.Label(fields_frame, text="Subject", bg="white", font=("Segoe UI", 10)).grid(row=1, column=0, sticky="w", padx=(0, 8), pady=6)
	subject_combo = ttk.Combobox(fields_frame, textvariable=subject_var, state="readonly", values=assigned_subjects, width=26)
	subject_combo.grid(row=1, column=1, sticky="w", padx=(0, 18), pady=6)

	tk.Label(fields_frame, text="Semester", bg="white", font=("Segoe UI", 10)).grid(row=1, column=2, sticky="w", padx=(0, 8), pady=6)
	ttk.Combobox(fields_frame, textvariable=semester_var, state="readonly", values=["I", "II", "III", "IV", "V", "VI", "VII", "VIII"], width=10).grid(row=1, column=3, sticky="w", pady=6)

	tk.Label(fields_frame, text="Assignment (10)", bg="white", font=("Segoe UI", 10)).grid(row=2, column=0, sticky="w", padx=(0, 8), pady=6)
	tk.Entry(fields_frame, textvariable=assignment_var, width=12).grid(row=2, column=1, sticky="w", pady=6)

	tk.Label(fields_frame, text="Attendance (10)", bg="white", font=("Segoe UI", 10)).grid(row=2, column=2, sticky="w", padx=(0, 8), pady=6)
	tk.Entry(fields_frame, textvariable=attendance_var, width=12).grid(row=2, column=3, sticky="w", pady=6)

	tk.Label(fields_frame, text="CT1 (10)", bg="white", font=("Segoe UI", 10)).grid(row=3, column=0, sticky="w", padx=(0, 8), pady=6)
	tk.Entry(fields_frame, textvariable=ct1_var, width=12).grid(row=3, column=1, sticky="w", pady=6)

	tk.Label(fields_frame, text="CT2 (10)", bg="white", font=("Segoe UI", 10)).grid(row=3, column=2, sticky="w", padx=(0, 8), pady=6)
	tk.Entry(fields_frame, textvariable=ct2_var, width=12).grid(row=3, column=3, sticky="w", pady=6)

	tk.Label(fields_frame, text="CT3 (10)", bg="white", font=("Segoe UI", 10)).grid(row=4, column=0, sticky="w", padx=(0, 8), pady=6)
	tk.Entry(fields_frame, textvariable=ct3_var, width=12).grid(row=4, column=1, sticky="w", pady=6)

	ct_best_label.grid(row=4, column=2, sticky="w", padx=(0, 8), pady=6)
	total_label.grid(row=4, column=3, sticky="w", pady=6)

	tree = ttk.Treeview(
		content,
		columns=("id", "enrollment", "name", "subject", "semester", "assignment", "attendance", "ct1", "ct2", "ct3", "best2", "internal"),
		show="headings",
		height=14,
	)
	for col, width in [
		("id", 50), ("enrollment", 110), ("name", 150), ("subject", 130), ("semester", 70),
		("assignment", 85), ("attendance", 85), ("ct1", 70), ("ct2", 70), ("ct3", 70), ("best2", 80), ("internal", 85),
	]:
		tree.heading(col, text=col.title())
		tree.column(col, width=width, anchor="center")
	tree.pack(fill="both", expand=True, padx=4, pady=(6, 0))

	def to_mark(raw):
		value = float(raw)
		if value < 0 or value > 10:
			raise ValueError
		return round(value, 2)

	def calculate_totals():
		assignment = to_mark(assignment_var.get().strip() or "0")
		attendance = to_mark(attendance_var.get().strip() or "0")
		ct1 = to_mark(ct1_var.get().strip() or "0")
		ct2 = to_mark(ct2_var.get().strip() or "0")
		ct3 = to_mark(ct3_var.get().strip() or "0")
		best_two = round(sum(sorted([ct1, ct2, ct3], reverse=True)[:2]), 2)
		internal_total = round(assignment + attendance + best_two, 2)
		return assignment, attendance, ct1, ct2, ct3, best_two, internal_total

	def refresh_preview(*_args):
		try:
			_, _, _, _, _, best_two, internal_total = calculate_totals()
			ct_best_label.config(text=f"CT Best Two: {best_two} / 20")
			total_label.config(text=f"Internal Total: {internal_total} / 40")
		except Exception:
			ct_best_label.config(text="CT Best Two: -")
			total_label.config(text="Internal Total: -")

	def refresh_table():
		for item in tree.get_children():
			tree.delete(item)

		conn = get_connection()
		cur = conn.cursor()
		where = []
		params = []
		if teacher_username:
			where.append("r.teacher_username=%s")
			params.append(teacher_username)
		if teacher_department:
			where.append("s.department=%s")
			params.append(teacher_department)
		if course_filter_var.get().strip() != "All":
			where.append("s.course=%s")
			params.append(course_filter_var.get().strip())
		if sem_filter_var.get().strip() != "All":
			where.append("s.semester=%s")
			params.append(sem_filter_var.get().strip())
		if section_filter_var.get().strip() != "All":
			where.append("s.section=%s")
			params.append(section_filter_var.get().strip())

		query = """
			SELECT r.id, r.enrollment_no, COALESCE(s.name,''), r.subject, r.semester,
				   r.assignment, r.attendance, r.ct1, r.ct2, r.ct3, r.ct_best_two, r.internal_total
			FROM teacher_internal_results r
			LEFT JOIN students s ON s.enrollment_no=r.enrollment_no
		"""
		if where:
			query += " WHERE " + " AND ".join(where)
		query += " ORDER BY r.updated_at DESC LIMIT 300"
		cur.execute(query, tuple(params))
		rows = cur.fetchall()
		conn.close()

		for row in rows:
			tree.insert("", "end", values=row)

	def export_excel_file():
		rows = [tree.item(item, "values") for item in tree.get_children()]
		if not rows:
			messagebox.showwarning("Export", "No internal marks available to export.")
			return

		file_path = filedialog.asksaveasfilename(
			title="Export Internal Marks to Excel",
			defaultextension=".xlsx",
			filetypes=[("Excel Workbook", "*.xlsx")],
			initialfile=f"internal_marks_{teacher_username or 'teacher'}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
		)
		if not file_path:
			return

		try:
			openpyxl = importlib.import_module("openpyxl")
			workbook = openpyxl.Workbook()
			sheet = workbook.active
			sheet.title = "Internal Marks"

			headers = [
				"ID", "Enrollment", "Student Name", "Subject", "Semester", "Assignment",
				"Attendance", "CT1", "CT2", "CT3", "CT Best Two", "Internal Total",
			]
			sheet.append(headers)

			for row in rows:
				sheet.append(list(row))

			workbook.save(file_path)
			messagebox.showinfo("Export", "Internal marks exported to Excel successfully.")
		except Exception as e:
			messagebox.showerror(
				"Export Error",
				f"Excel export failed: {str(e)}\nInstall package: pip install openpyxl",
			)

	def export_pdf_file():
		rows = [tree.item(item, "values") for item in tree.get_children()]
		if not rows:
			messagebox.showwarning("Export", "No internal marks available to export.")
			return

		file_path = filedialog.asksaveasfilename(
			title="Export Internal Marks to PDF",
			defaultextension=".pdf",
			filetypes=[("PDF Document", "*.pdf")],
			initialfile=f"internal_marks_{teacher_username or 'teacher'}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
		)
		if not file_path:
			return

		try:
			report_canvas = importlib.import_module("reportlab.pdfgen.canvas")
			pagesize_module = importlib.import_module("reportlab.lib.pagesizes")
			landscape_fn = getattr(pagesize_module, "landscape")
			A4 = getattr(pagesize_module, "A4")

			pdf = report_canvas.Canvas(file_path, pagesize=landscape_fn(A4))
			width, height = landscape_fn(A4)

			pdf.setFont("Helvetica-Bold", 12)
			pdf.drawString(40, height - 35, "Internal Marks Evaluation Report")
			pdf.setFont("Helvetica", 9)
			pdf.drawString(40, height - 52, f"Generated: {datetime.now().strftime('%d-%b-%Y %I:%M %p')}")

			headers = ["Enroll", "Name", "Subject", "Sem", "Assign", "Attend", "CT1", "CT2", "CT3", "Best2", "Internal"]
			col_widths = [70, 120, 95, 40, 50, 50, 35, 35, 35, 45, 55]

			x = 40
			y = height - 80
			pdf.setFont("Helvetica-Bold", 8)
			for index, head in enumerate(headers):
				pdf.drawString(x, y, head)
				x += col_widths[index]

			y -= 14
			pdf.setFont("Helvetica", 8)
			for row in rows:
				x = 40
				values = [
					str(row[1])[:12], str(row[2])[:22], str(row[3])[:16], str(row[4])[:8],
					str(row[5]), str(row[6]), str(row[7]), str(row[8]), str(row[9]), str(row[10]), str(row[11]),
				]
				for index, value in enumerate(values):
					pdf.drawString(x, y, value)
					x += col_widths[index]

				y -= 13
				if y < 35:
					pdf.showPage()
					y = height - 35
					pdf.setFont("Helvetica", 8)

			pdf.save()
			messagebox.showinfo("Export", "Internal marks exported to PDF successfully.")
		except Exception as e:
			messagebox.showerror(
				"Export Error",
				f"PDF export failed: {str(e)}\nInstall package: pip install reportlab",
			)

	def on_enrollment_change(_event=None):
		enrollment = enrollment_var.get().strip()
		info = student_map.get(enrollment)
		if info:
			student_name_var.set(info[0] or "")
			if info[1]:
				semester_var.set(str(info[1]))
		else:
			student_name_var.set("")

	def refresh_student_list(*_args):
		nonlocal students, student_map
		students = get_students(
			course_filter_var.get().strip(),
			sem_filter_var.get().strip(),
			section_filter_var.get().strip(),
		)
		student_map = {row[0]: (row[1], row[2]) for row in students}
		enrollment_combo["values"] = [row[0] for row in students]
		enrollment_var.set("")
		student_name_var.set("")
		refresh_table()

	def refresh_course_filters(*_args):
		courses = ["All"] + get_distinct_values("course")
		course_combo_filter["values"] = courses
		if course_filter_var.get() not in courses:
			course_filter_var.set("All")

	def refresh_semester_filters(*_args):
		semesters = ["All"] + get_distinct_values("semester", course_filter_var.get().strip())
		sem_combo_filter["values"] = semesters
		if sem_filter_var.get() not in semesters:
			sem_filter_var.set("All")

	def refresh_section_filters(*_args):
		sections = ["All"] + get_distinct_values("section", course_filter_var.get().strip(), sem_filter_var.get().strip())
		section_combo_filter["values"] = sections
		if section_filter_var.get() not in sections:
			section_filter_var.set("All")

	def on_course_filter_change(_event=None):
		refresh_semester_filters()
		refresh_section_filters()
		refresh_student_list()

	def on_semester_filter_change(_event=None):
		refresh_section_filters()
		refresh_student_list()

	def on_section_filter_change(_event=None):
		refresh_student_list()

	def clear_form():
		subject_var.set("")
		assignment_var.set("0")
		attendance_var.set("0")
		ct1_var.set("0")
		ct2_var.set("0")
		ct3_var.set("0")
		refresh_preview()

	def save_internal_marks():
		enrollment = enrollment_var.get().strip()
		subject = subject_var.get().strip()
		semester = semester_var.get().strip()

		if not enrollment:
			messagebox.showerror("Error", "Please select enrollment.")
			return
		if not subject:
			messagebox.showerror("Error", "Subject is required.")
			return
		if not semester:
			messagebox.showerror("Error", "Semester is required.")
			return

		try:
			assignment, attendance, ct1, ct2, ct3, best_two, internal_total = calculate_totals()
		except Exception:
			messagebox.showerror("Error", "Marks must be numeric between 0 and 10.")
			return

		conn = get_connection()
		cur = conn.cursor()
		cur.execute("SELECT enrollment_no FROM students WHERE enrollment_no=%s", (enrollment,))
		if not cur.fetchone():
			conn.close()
			messagebox.showerror("Error", "Selected enrollment does not exist.")
			return

		cur.execute(
			"""
			INSERT INTO teacher_internal_results
			(enrollment_no, subject, semester, assignment, attendance, ct1, ct2, ct3, ct_best_two, internal_total, teacher_username)
			VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
			ON DUPLICATE KEY UPDATE
				assignment=VALUES(assignment),
				attendance=VALUES(attendance),
				ct1=VALUES(ct1),
				ct2=VALUES(ct2),
				ct3=VALUES(ct3),
				ct_best_two=VALUES(ct_best_two),
				internal_total=VALUES(internal_total),
				teacher_username=VALUES(teacher_username)
			""",
			(enrollment, subject, semester, assignment, attendance, ct1, ct2, ct3, best_two, internal_total, teacher_username),
		)

		cur.execute(
			"""
			INSERT INTO results (enrollment_no, subject, marks, exam, teacher_username)
			VALUES (%s,%s,%s,'Internal',%s)
			ON DUPLICATE KEY UPDATE marks=VALUES(marks), teacher_username=VALUES(teacher_username)
			""",
			(enrollment, subject, internal_total, teacher_username),
		)

		conn.commit()
		conn.close()

		messagebox.showinfo("Success", "Internal marks saved successfully.")
		refresh_table()
		if callable(update_stats_callback):
			update_stats_callback()

	def on_tree_select(_event=None):
		selected = tree.focus()
		if not selected:
			return
		values = tree.item(selected, "values")
		if not values:
			return

		enrollment_var.set(str(values[1]))
		student_name_var.set(str(values[2]))
		subject_var.set(str(values[3]))
		semester_var.set(str(values[4]))
		assignment_var.set(str(values[5]))
		attendance_var.set(str(values[6]))
		ct1_var.set(str(values[7]))
		ct2_var.set(str(values[8]))
		ct3_var.set(str(values[9]))
		refresh_preview()

	btn_row = tk.Frame(form, bg="white")
	btn_row.pack(fill="x", padx=16, pady=(0, 14))

	tk.Button(
		btn_row,
		text="Save / Update Internal",
		command=save_internal_marks,
		bg="#1abc9c",
		fg="white",
		bd=0,
		padx=16,
		pady=8,
		font=("Segoe UI", 10, "bold"),
	).pack(side="left")

	tk.Button(
		btn_row,
		text="Clear",
		command=clear_form,
		bg="#7f8c8d",
		fg="white",
		bd=0,
		padx=14,
		pady=8,
		font=("Segoe UI", 10),
	).pack(side="left", padx=8)

	ttk.Button(
		btn_row,
		text="Export Excel",
		command=export_excel_file,
		style="Accent.TButton",
	).pack(side="left", padx=8)

	ttk.Button(
		btn_row,
		text="Export PDF",
		command=export_pdf_file,
		style="Accent.TButton",
	).pack(side="left", padx=4)

	tk.Label(
		btn_row,
		text="Rule: Assignment 10 + Attendance 10 + Best 2 CTs(20) = Internal 40",
		bg="white",
		fg="#34495e",
		font=("Segoe UI", 10, "italic"),
	).pack(side="right")

	enrollment_combo.bind("<<ComboboxSelected>>", on_enrollment_change)
	course_combo_filter.bind("<<ComboboxSelected>>", on_course_filter_change)
	sem_combo_filter.bind("<<ComboboxSelected>>", on_semester_filter_change)
	section_combo_filter.bind("<<ComboboxSelected>>", on_section_filter_change)
	tree.bind("<<TreeviewSelect>>", on_tree_select)

	for variable in [assignment_var, attendance_var, ct1_var, ct2_var, ct3_var]:
		variable.trace_add("write", refresh_preview)

	refresh_course_filters()
	refresh_semester_filters()
	refresh_section_filters()
	refresh_student_list()
	refresh_preview()
