export type ImportFailure = {
  row_number: number;
  reason: string;
};

export type QuestionImportResult = {
  success_count: number;
  failed_count: number;
  failures: ImportFailure[];
};
