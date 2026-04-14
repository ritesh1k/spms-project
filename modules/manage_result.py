import tkinter as tk
from tkinter import ttk, messagebox

from db_config import get_connection
from modules.result_utils import ensure_result_tables, grade_for_score, promote_student_if_passed


def load_module(parent_frame, update_stats_callback=None):
	for widget in parent_frame.winfo_children():
		widget.destroy()
	parent_frame.configure(bg="#f5f7fa")

	ensure_result_tables(include_published=True)

	title_frame = tk.Frame(parent_frame, bg="#9b59b6", height=60)
	title_frame.pack(fill="x")
	title_frame.pack_propagate(False)

	tk.Label(
		title_frame,
		text="📢 Publish Result",
		font=("Segoe UI", 16, "bold"),
		bg="#9b59b6",
		fg="white",
	).pack(pady=12)

	content = tk.Frame(parent_frame, bg="#f5f7fa")
	content.pack(fill="both", expand=True, padx=16, pady=16)

	control = tk.Frame(content, bg="white", bd=1, relief="solid")
	control.pack(fill="x", pady=(0, 10))

	control_inner = tk.Frame(control, bg="white")
	control_inner.pack(pady=8)

	enrollment_filter_var = tk.StringVar()
	external_var = tk.StringVar(value="0")
	selected_internal_id = {"id": None}

	summary_var = tk.StringVar(value="Select an internal record to publish result.")

	columns = (
		"internal_id", "enrollment", "name", "subject", "semester", "assignment", "attendance",
		"ct1", "ct2", "ct3", "ct_best_two", "internal_total", "teacher",
	)
	internal_tree = ttk.Treeview(content, columns=columns, show="headings", height=10)
	for col, width in [
		("internal_id", 70), ("enrollment", 100), ("name", 130), ("subject", 120), ("semester", 70),
		("assignment", 80), ("attendance", 80), ("ct1", 55), ("ct2", 55), ("ct3", 55),
		("ct_best_two", 85), ("internal_total", 85), ("teacher", 100),
	]:
		internal_tree.heading(col, text=col.replace("_", " ").title())
		internal_tree.column(col, width=width, anchor="center")
	internal_tree.pack(fill="x", pady=(0, 10))

	publish_box = tk.Frame(content, bg="white", bd=1, relief="solid")
	publish_box.pack(fill="x", pady=(0, 10))

	tk.Label(control_inner, text="Enrollment", background="white", font=("Segoe UI", 10)).pack(side="left", padx=(8, 6), pady=8)
	tk.Entry(control_inner, textvariable=enrollment_filter_var, width=16).pack(side="left", padx=(0, 10), pady=8)

	publish_inner = tk.Frame(publish_box, bg="white")
	publish_inner.pack(pady=8)

	tk.Label(publish_inner, text="External Marks (0-60)", background="white", font=("Segoe UI", 10)).pack(side="left", padx=(8, 8), pady=8)
	tk.Entry(publish_inner, textvariable=external_var, width=10).pack(side="left", pady=8)

	tk.Label(publish_inner, textvariable=summary_var, background="white", foreground="#1f2937", font=("Segoe UI", 10, "bold")).pack(side="left", padx=16, pady=8)

	published_columns = (
		"id", "enrollment", "name", "subject", "semester", "internal_total", "external_marks", "final_total", "grade", "status", "published_by",
	)
	published_tree = ttk.Treeview(content, columns=published_columns, show="headings", height=9)
	for col, width in [
		("id", 55), ("enrollment", 100), ("name", 140), ("subject", 120), ("semester", 70),
		("internal_total", 85), ("external_marks", 90), ("final_total", 90), ("grade", 65), ("status", 80), ("published_by", 95),
	]:
		published_tree.heading(col, text=col.replace("_", " ").title())
		published_tree.column(col, width=width, anchor="center")
	published_tree.pack(fill="both", expand=True)

	def refresh_internal():
		for item in internal_tree.get_children():
			internal_tree.delete(item)

		enrollment_text = enrollment_filter_var.get().strip()

		conn = get_connection()
		cur = conn.cursor()
		if enrollment_text:
			cur.execute(
				"""
				SELECT r.id, r.enrollment_no, COALESCE(s.name,''), r.subject, r.semester,
					   r.assignment, r.attendance, r.ct1, r.ct2, r.ct3, r.ct_best_two, r.internal_total,
					   COALESCE(r.teacher_username,'')
				FROM teacher_internal_results r
				LEFT JOIN students s ON s.enrollment_no=r.enrollment_no
				WHERE r.enrollment_no LIKE %s
				ORDER BY r.updated_at DESC
				LIMIT 500
				""",
				(f"%{enrollment_text}%",),
			)
		else:
			cur.execute(
				"""
				SELECT r.id, r.enrollment_no, COALESCE(s.name,''), r.subject, r.semester,
					   r.assignment, r.attendance, r.ct1, r.ct2, r.ct3, r.ct_best_two, r.internal_total,
					   COALESCE(r.teacher_username,'')
				FROM teacher_internal_results r
				LEFT JOIN students s ON s.enrollment_no=r.enrollment_no
				ORDER BY r.updated_at DESC
				LIMIT 500
				"""
			)
		rows = cur.fetchall()
		conn.close()

		for row in rows:
			internal_tree.insert("", "end", values=row)

	def refresh_published():
		for item in published_tree.get_children():
			published_tree.delete(item)

		conn = get_connection()
		cur = conn.cursor()
		cur.execute(
			"""
			SELECT p.id, p.enrollment_no, COALESCE(s.name,''), p.subject, p.semester,
				   p.internal_total, p.external_marks, p.final_total, p.grade, p.status,
				   COALESCE(p.published_by,'')
			FROM published_results p
			LEFT JOIN students s ON s.enrollment_no=p.enrollment_no
			ORDER BY p.published_at DESC
			LIMIT 500
			"""
		)
		rows = cur.fetchall()
		conn.close()

		for row in rows:
			published_tree.insert("", "end", values=row)

	def on_internal_select(_event=None):
		selected = internal_tree.focus()
		if not selected:
			return
		values = internal_tree.item(selected, "values")
		if not values:
			return
		selected_internal_id["id"] = int(values[0])
		summary_var.set(
			f"{values[1]} | {values[3]} | Sem {values[4]} | Internal {values[11]}/40"
		)

	def publish_result():
		internal_id = selected_internal_id["id"]
		if not internal_id:
			messagebox.showerror("Error", "Please select an internal record first.")
			return

		try:
			external_marks = round(float(external_var.get().strip()), 2)
		except Exception:
			messagebox.showerror("Error", "External marks must be numeric.")
			return

		if external_marks < 0 or external_marks > 60:
			messagebox.showerror("Error", "External marks must be between 0 and 60.")
			return

		conn = get_connection()
		cur = conn.cursor()
		cur.execute(
			"""
			SELECT enrollment_no, subject, semester, assignment, attendance, ct1, ct2, ct3, ct_best_two, internal_total, teacher_username
			FROM teacher_internal_results WHERE id=%s
			""",
			(internal_id,),
		)
		row = cur.fetchone()
		if not row:
			conn.close()
			messagebox.showerror("Error", "Internal result record not found.")
			return

		enrollment_no, subject, semester, assignment, attendance, ct1, ct2, ct3, ct_best_two, internal_total, teacher_username = row
		final_total = round(float(internal_total) + external_marks, 2)
		status = "Pass" if final_total >= 40 else "Fail"
		grade = grade_for_score(final_total)

		cur.execute(
			"""
			INSERT INTO published_results
			(enrollment_no, subject, semester, assignment, attendance, ct1, ct2, ct3, ct_best_two, internal_total,
			 external_marks, final_total, grade, status, published_by)
			VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'admin')
			ON DUPLICATE KEY UPDATE
				assignment=VALUES(assignment),
				attendance=VALUES(attendance),
				ct1=VALUES(ct1),
				ct2=VALUES(ct2),
				ct3=VALUES(ct3),
				ct_best_two=VALUES(ct_best_two),
				internal_total=VALUES(internal_total),
				external_marks=VALUES(external_marks),
				final_total=VALUES(final_total),
				grade=VALUES(grade),
				status=VALUES(status),
				published_by=VALUES(published_by),
				published_at=CURRENT_TIMESTAMP
			""",
			(
				enrollment_no, subject, semester, assignment, attendance, ct1, ct2, ct3,
				ct_best_two, internal_total, external_marks, final_total, grade, status,
			),
		)

		cur.execute(
			"""
			INSERT INTO results (enrollment_no, subject, marks, exam, teacher_username)
			VALUES (%s,%s,%s,'Final exams',%s)
			ON DUPLICATE KEY UPDATE marks=VALUES(marks), teacher_username=VALUES(teacher_username)
			""",
			(enrollment_no, subject, final_total, teacher_username),
		)

		conn.commit()
		conn.close()

		promote_student_if_passed(enrollment_no, final_total)
		messagebox.showinfo("Published", "Result published successfully.")
		refresh_internal()
		refresh_published()
		if callable(update_stats_callback):
			update_stats_callback()

	btn_row = tk.Frame(control_inner, bg="white")
	btn_row.pack(side="left", padx=6, pady=6)

	tk.Button(btn_row, text="Search", command=refresh_internal, bg="#3498db", fg="white", bd=0, padx=12, pady=6).pack(side="left", padx=4)
	tk.Button(btn_row, text="Publish Result", command=publish_result, bg="#16a085", fg="white", bd=0, padx=12, pady=6).pack(side="left", padx=4)
	tk.Button(btn_row, text="Refresh Published", command=refresh_published, bg="#7f8c8d", fg="white", bd=0, padx=12, pady=6).pack(side="left", padx=4)

	internal_tree.bind("<<TreeviewSelect>>", on_internal_select)

	refresh_internal()
	refresh_published()
