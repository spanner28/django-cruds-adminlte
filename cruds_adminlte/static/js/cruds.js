$(function(){
	$('select').select2();
	$('input').iCheck({
		checkboxClass: 'icheckbox_minimal-blue',
		radioClass: 'iradio_minimal-blue',
	});
	$('.datetimeinput').datetimepicker({
		inline: true,
                sideBySide: true,
		format: 'yyyy-mm-dd hh:ii'
	});
	$('.timeinput').datetimepicker({
		format: 'hh:ii',
		language: 'en',
		pick12HourFormat: true
	});
	$('.dateinput').datepicker({
		format: 'yyyy-mm-dd'
	});
});
