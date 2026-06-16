export type Candidate = {
  id: number;
  token?: string;
  name: string;
  employee_no?: string | null;
  department?: string | null;
  position?: string | null;
  phone_suffix?: string | null;
  email?: string | null;
  exam_group?: string | null;
  should_attend: boolean;
  status: string;
  remark?: string | null;
};
