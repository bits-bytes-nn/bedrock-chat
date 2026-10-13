import dayjs, { ManipulateType } from 'dayjs';
import customParseFormat from 'dayjs/plugin/customParseFormat';
import utc from 'dayjs/plugin/utc';

dayjs.extend(customParseFormat);
dayjs.extend(utc);

const DEFAULT_DATETIME_FORMAT = 'YYYY/MM/DD HH:mm:ss';
const DEFAULT_DATE_FORMAT = 'YYYY/MM/DD';

export const formatDatetime = (date: dayjs.ConfigType, format?: string) => {
  return dayjs(date).format(format ?? DEFAULT_DATETIME_FORMAT);
};

export const formatDate = (date: dayjs.ConfigType, format?: string) => {
  return dayjs(date).format(format ?? DEFAULT_DATE_FORMAT);
};

export const addDate = (
  date: dayjs.ConfigType,
  value: number,
  unit?: ManipulateType
) => {
  return dayjs(date).add(value, unit).toDate();
};

/**
 * The UTC hour (`YYYYMMDDHH`) of an hour of a local date. The usage exports are
 * partitioned by UTC hour, so a local day maps to UTC hours that can span two dates.
 */
export const toUtcDateHour = (
  localDate: string,
  hour: number,
  format: string
): string | undefined => {
  const date = dayjs(localDate, format, true);
  return date.isValid()
    ? date.hour(hour).utc().format('YYYYMMDDHH')
    : undefined;
};

