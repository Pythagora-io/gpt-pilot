/* Send mail using nodemailer
 *
 * Configure using NODEMAILER_* env variables.
 * See https://nodemailer.com/smtp/ for all options
 *
 * Send mail with:
 *
 *   import transport from "./src/utils/mail.js";
 *   await transport.sendMail({ from, to, subject, text });
 *
 * For all message options, see: https://nodemailer.com/message/
 */
import nodemailer from "nodemailer";

import config from "./config.js";

const options = {
  host: config.NODEMAILER_HOST,
  port: config.NODEMAILER_PORT,
  secure: config.NODEMAILER_SECURE,
};

if (config.NODEMAILER_USER && config.NODMAILER_PASS) {
  options.auth = {
    user: config.NODEMAILER_USER,
    pass: config.NODEMAILER_PASS,
  };
}

const transporter = nodemailer.createTransport(options);
const sendMail = transporter.sendMail.bind(transporter);

export default sendMail;
