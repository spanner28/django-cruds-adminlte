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

jQuery(document).ready(function(){
    jQuery(jQuery('form')[0]).find('input[type="submit"]').click(function(e){
        jQuery('.requiredField').each(function(i, o) {
            if (jQuery(o).parent().find('.controls input').val() == '') {
                jQuery('.tab-content .tab-pane').removeClass('active');
                jQuery(o).parent().parent().addClass('active');
                tab_id = jQuery(o).parent().parent().attr('id')
                tab_index = 0;
                jQuery('.tab-content .tab-pane').each(function(ii, oo) {
                    tab_index += 1;
                    if (jQuery(oo).attr('id') == tab_id) {
                        return;
                    }
                })
                jQuery('.nav-tabs li').removeClass('active');
                jQuery(jQuery('.nav-tabs li')[1]).addClass('active');
                return false
            }
        })
    })
})
